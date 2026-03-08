import subprocess
import zipfile
import shutil
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).parent.resolve()

ANDROID_JAR = BASE_DIR / "tools" / "android.jar"
D8_BAT = BASE_DIR / "tools" / "d8.bat"
APKTOOL_JAR = BASE_DIR / "tools" / "apktool.jar"
ZIPALIGN_EXE = BASE_DIR / "tools" / "zipalign.exe"
APK_SIGNER_BAT = BASE_DIR / "tools" / "apksigner.bat"

JAVA_FILE = BASE_DIR / "Injector.java"

INPUT_APK = BASE_DIR / "mergedragons.apk"

WORK_DIR = BASE_DIR / "mergedragons"
CLASSES10_DEX = WORK_DIR / "classes10.dex"
CLASSES10_APK = BASE_DIR / "classes10.apk"
OUTPUT_SRC = BASE_DIR / "classes10_src"
RECOMPILED_APK = BASE_DIR / "classes10_recompiled.apk"
ALIGNED_APK = BASE_DIR / "classes10_aligned.apk"



def run(cmd: list):
    print(">>", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def compile_java():
    run([
        "javac",
        "-source", "8",
        "-target", "8",
        "-bootclasspath", str(ANDROID_JAR),
        "-classpath", str(ANDROID_JAR),
        str(JAVA_FILE)
    ])


def build_dex():
    class_files = list(BASE_DIR.glob("Injector*.class"))

    if not class_files:
        raise FileNotFoundError("Keine Injector*.class Dateien gefunden")

    run([
        D8_BAT,
        *[str(f) for f in class_files],
        "--min-api", "21",
        "--output", str(BASE_DIR)
    ])

def extract_apk():
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)

    WORK_DIR.mkdir()

    with zipfile.ZipFile(INPUT_APK, "r") as z:
        z.extractall(WORK_DIR)


def move_classes_dex():
    source = BASE_DIR / "classes.dex"
    if not source.exists():
        raise FileNotFoundError("classes.dex wurde nicht von d8 erzeugt")

    shutil.move(source, CLASSES10_DEX)

def move_lib():
    source = BASE_DIR / "libil2cppdumper.so"
    if not source.exists():
        raise FileNotFoundError("libil2cppdumper.so nicht gefunden")

    target = WORK_DIR / "lib" / "arm64-v8a" / "libil2cppdumper.so"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def rebuild_apk():
    if CLASSES10_APK.exists():
        CLASSES10_APK.unlink()

    with zipfile.ZipFile(CLASSES10_APK, "w", zipfile.ZIP_DEFLATED) as z:
        for file in WORK_DIR.rglob("*"):
            z.write(file, file.relative_to(WORK_DIR))


def decompile_with_apktool():
    run([
        "java",
        "-jar", str(APKTOOL_JAR),
        "d",
        str(CLASSES10_APK),
        "-o", str(OUTPUT_SRC),
        "-f"
    ])

def patch_unity_player_activity(base_dir: Path):
    target_file = (
        base_dir
        / "classes10_src"
        / "smali_classes8"
        / "com"
        / "gramgames"
        / "activity"
        / "UnityPlayerActivity.smali"
    )

    if not target_file.exists():
        raise FileNotFoundError(f"{target_file} nicht gefunden")

    with target_file.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    method_signature = ".method protected onCreate(Landroid/os/Bundle;)V"
    invoke_super_prefix = "invoke-super"
    injection_line = "    invoke-static {p0}, Lcom/inject/Injector;->init(Landroid/content/Context;)V\n"

    in_method = False
    patched = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith(method_signature):
            in_method = True
            continue

        if in_method:
            if stripped.startswith(".end method"):
                break

            # Schon gepatcht?
            if "Lcom/inject/Injector;->init" in stripped:
                patched = True
                break

            if stripped.startswith(invoke_super_prefix):
                lines.insert(i, injection_line)
                patched = True
                break

    if not patched:
        raise RuntimeError("Patch konnte nicht angewendet werden")

    with target_file.open("w", encoding="utf-8") as f:
        f.writelines(lines)

def patch_android_manifest(base_dir: Path):
    manifest_path = base_dir / "classes10_src" / "AndroidManifest.xml"

    if not manifest_path.exists():
        raise FileNotFoundError("AndroidManifest.xml nicht gefunden")

    ET.register_namespace("android", "http://schemas.android.com/apk/res/android")

    tree = ET.parse(manifest_path)
    root = tree.getroot()

    android_ns = "{http://schemas.android.com/apk/res/android}"

    required_permissions = [
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        # Optional für Android 11+ (Play Store kritisch!)
        # "android.permission.MANAGE_EXTERNAL_STORAGE",
    ]

    existing_permissions = {
        elem.attrib.get(android_ns + "name")
        for elem in root.findall("uses-permission")
    }

    for perm in required_permissions:
        if perm not in existing_permissions:
            perm_element = ET.Element("uses-permission")
            perm_element.set(android_ns + "name", perm)
            root.insert(0, perm_element)

    # requestLegacyExternalStorage setzen (nur falls application existiert)
    application = root.find("application")
    if application is None:
        raise RuntimeError("<application> Tag nicht gefunden")

    if application.get(android_ns + "requestLegacyExternalStorage") != "true":
        application.set(android_ns + "requestLegacyExternalStorage", "true")

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)

def recompile_with_apktool():
    run([
        "java",
        "-jar", str(APKTOOL_JAR),
        "b",
        str(OUTPUT_SRC),
        "-o", str(RECOMPILED_APK),
        "-f"
    ])

def align_apk():
    run([
        ZIPALIGN_EXE,
        "-v",
        "4",
        str(RECOMPILED_APK),
        str(ALIGNED_APK)
    ])

def generate_key():
    run([
        "keytool",
        "-genkey",
        "-v",
        "-keystore", str(BASE_DIR / "debug.keystore"),
        "-storepass", "android",
        "-keypass", "android",
        "-alias", "androiddebugkey",
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-dname", "CN=Android Debug,O=Android,C=US"
    ])


def sign_apk():
    run([
        APK_SIGNER_BAT,
        "sign",
        "--ks", str(BASE_DIR / "debug.keystore"),
        "--ks-key-alias", "androiddebugkey",
        "--ks-pass", "pass:android",
        str(ALIGNED_APK)
    ])

def cleanup():
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    if OUTPUT_SRC.exists():
        shutil.rmtree(OUTPUT_SRC)
    if RECOMPILED_APK.exists():
        RECOMPILED_APK.unlink()
    if CLASSES10_APK.exists():
        CLASSES10_APK.unlink()
    if CLASSES10_DEX.exists():
        CLASSES10_DEX.unlink()
    if (BASE_DIR / "classes10_aligned.apk.idsig").exists():
        (BASE_DIR / "classes10_aligned.apk.idsig").unlink()
    if (BASE_DIR / "debug.keystore").exists():
        (BASE_DIR / "debug.keystore").unlink()
    class_files = list(BASE_DIR.glob("Injector*.class"))
    for cf in class_files:
        cf.unlink()

def main():
    print("Starting Injection...")
    if (INPUT_APK.exists()):
        print("APK already exists, skipping extraction")
    else:
        print("Extracting APK...")
        run(["mergedragons.exe"])
    print("Cleanup...")
    cleanup()
    print("Compile Java...")
    compile_java()
    print("Build DEX...")
    build_dex()
    print("Extract APK...")
    extract_apk()
    print("Move classes.dex...")
    move_classes_dex()
    #print("Move lib...")
    #move_lib()
    print("Rebuild APK...")
    rebuild_apk()
    print("Decompile with Apktool...")
    decompile_with_apktool()
    print("Patch UnityPlayerActivity...")
    patch_unity_player_activity(BASE_DIR)
    print("Patch AndroidManifest...")
    patch_android_manifest(BASE_DIR)
    print("Recompile with Apktool...")
    recompile_with_apktool()
    print("Align APK...")
    align_apk()
    print("Generate key...")
    generate_key()
    print("Sign APK...")
    sign_apk()
    print("Cleanup...")
    cleanup()
    shutil.move(ALIGNED_APK, BASE_DIR / "mergedragons_injected.apk")
    print("Fertig.")


if __name__ == "__main__":
    main()