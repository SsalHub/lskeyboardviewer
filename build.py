import PyInstaller.__main__
import version
import os

def create_version_info():
    v_parts = version.VERSION.split('.')
    while len(v_parts) < 4:
        v_parts.append('0')
    v_tuple = tuple(map(int, v_parts))
    v_str = version.VERSION

    info_content = f"""
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v_tuple},
    prodvers={v_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'041204b0',
        [StringStruct(u'CompanyName', u'{version.AUTHOR}'),
        StringStruct(u'FileDescription', u'LostSaga Keyboard Viewer'),
        StringStruct(u'FileVersion', u'{v_str}'),
        StringStruct(u'InternalName', u'LSKeyboardViewer'),
        StringStruct(u'OriginalFilename', u'LSKeyboardViewer.exe'),
        StringStruct(u'ProductName', u'LostSaga Keyboard Viewer'),
        StringStruct(u'ProductVersion', u'{v_str}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1042, 1200])])
  ]
)
"""
    # StringStruct(u'LegalCopyright', u'Copyright (c) {version.YEAR}. {version.AUTHOR} All rights reserved.'),
    
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(info_content.strip())
    print(f"? version_info.txt generated! (version: {v_str})")

def build():
    create_version_info()

    print("building start...")
    
    PyInstaller.__main__.run([
        'app.py',                       
        '--noconsole',                 
        # '--onefile',                    
        '--onedir',                    
        # '--runtime-tmpdir=.',           
        '--version-file=version_info.txt', 
        '--add-data=resource;resource', 
        '--name=LSKeyboardViewer',     
        '--icon=icon.ico',
        '--clean',                     
    ])
    
    if os.path.exists("version_info.txt"):
        os.remove("version_info.txt")
        
    print("\n build complete! check out '.\\dist'.")

if __name__ == "__main__":
    build()