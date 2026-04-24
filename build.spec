# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 将图标文件和模型文件打包进exe内
    datas=[
        ('laughter_can.ico', '.'),
        ('assets/models/yamnet.tflite', 'assets/models')
    ],
    # 强制导入有些时候不会被自动追踪到的底层库
    hiddenimports=['sounddevice', 'pynput', 'keyboard', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='笑声罐头',             # 生成的 exe 名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                  # 是否使用 UPX 压缩代码（如果安装了的话）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # False 代表隐藏黑框控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['laughter_can.ico'], # exe 程序的外部系统图标
)