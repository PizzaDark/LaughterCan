# 笑声罐头

## 作者：[@依然匹萨吧](https://space.bilibili.com/6297797)

## 项目简介

**笑声罐头** 是一款基于 **PyQt6** 和 **YAMNet** 笑声检测的音效播放器。程序会通过麦克风输入识别笑声类型，也支持鼠标手势和快捷键手动触发，并从本地音频池中随机播放匹配的笑声文件。

它适合做整活、直播互动、桌面娱乐或自定义音效触发器。程序支持标签筛选、文件名搜索、音频管理、音笑包导入和系统托盘后台运行。

## 功能介绍

**[介绍视频](https://www.bilibili.com/video/BV1c6RMB8ERV)**

### 1. 笑声识别与触发

- 程序支持导入音笑包(一个含有音频文件和规则集 `rule.json` 的文件夹，`rule.json` 会在启动后自动生成)。导入后会切换到新的规则集和音频数据，适合在不同的音频集合之间快速切换。
- 使用麦克风监听环境声音。
- 基于 YAMNet TFLite 模型识别笑声类别。
- 支持 `普通笑`、`婴儿笑`、`咯咯笑`、`窃笑`、`开怀大笑`、`憨笑` 等类别。
- 内置冷却机制，减少连续误触。

### 2. 多种触发方式
- **麦克风识别触发**：检测到对应笑声后自动播放。
- **鼠标手势触发**：识别近似圆形轨迹后触发随机笑声。
- **快捷键触发**：可自定义热键，一键播放当前筛选条件下的随机音频。

### 3. 音频池管理
- 支持添加、删除、修改本地音频条目。
- 可设置每个音频的笑声类别、启用状态和标签。
- 支持一键导入音笑包目录。
- 支持从规则集目录打开 `rule.json` 所在位置。

### 4. 标签与筛选
- 支持为音频添加多个标签。
- 支持标签颜色管理，便于区分。
- 可按标签筛选可播放音频。
- 支持按文件名关键字搜索。

## 文件说明

```text
├── main.py                  # 主程序入口，包含界面、识别、播放与管理逻辑
├── build.spec               # PyInstaller 打包配置
├── requirements.txt         # Python 依赖列表
├── run.bat                  # Windows 快速启动脚本
├── rule.json                # 规则与音频数据配置
├── assets/
│   └── models/
│       └── yamnet.tflite    # 音频识别模型
└── LICENSE                  # 许可证文件
```

## 环境要求

- **操作系统**：Windows 10 / 11 优先，源码运行也可在其他系统上尝试。
- **Python**：3.10 或更高版本。
- **麦克风**：用于实时语音与笑声识别。
- **音频输出设备**：用于播放笑声文件。

## 快速开始

### 运行发布版本

如果你已经拿到打包好的程序，直接运行 `.exe` 即可。

### 从源码运行

#### 方法一：使用批处理脚本

在 Windows 环境下，直接双击运行 [`run.bat`](run.bat)。

在 macOS/Linux 环境下，执行:

```sh
chmod +x run.sh
./run.sh
```

#### 方法二：手动运行

1. **获取项目源码**

   ```bash
   git clone https://github.com/PizzaDark/LaughterCan.git
   cd LaughterCan
   ```

2. **安装依赖**

   ```bash
   # 推荐使用 Python 3.10+
   python -m venv .venv
   .venv\Scripts\activate # Windows
   source .venv/bin/activate # macOS/Linux
   
   pip install -r requirements.txt
   ```

3. **运行程序**

   ```bash
   python main.py
   ```
   
4. **[规则集示例](rule.example.json)**

   ```json
{
       "hotkeys": {
           "random": "k"
       },
       "tags": [
           "曹操",
           "董卓",
           "刘备",
           "张飞",
           "关羽"
       ],
       "active_tag": "全部",
       "audios": [
           {
               "path": "曹操_咯咯笑1.mp3",
               "type": "giggle",
               "tags": [
                   "曹操"
               ],
               "enabled": true
           },
           {
               "path": "曹操_憨笑1.mp3",
               "type": "chuckle",
               "tags": [
                   "曹操"
               ],
               "enabled": true
           },
           {
               "path": "董卓_开怀大笑1.mp3",
               "type": "belly_laugh",
               "tags": [
                   "董卓"
               ],
               "enabled": true
           },
           {
               "path": "刘备_窃笑1.mp3",
               "type": "snicker",
               "tags": [
                   "刘备"
               ],
               "enabled": true
           },
           {
               "path": "张飞_婴儿笑1.mp3",
               "type": "baby_laughter",
               "tags": [
                   "张飞"
               ],
               "enabled": true
           },
           {
               "path": "张飞_婴儿笑2.mp3",
               "type": "baby_laughter",
               "tags": [
                   "张飞"
               ],
               "enabled": false
           },
           {
               "path": "关羽_普通笑1.mp3",
               "type": "laughter",
               "tags": [
                   "关羽"
               ],
               "enabled": true
           }
       ],
       "tag_colors": {
           "曹操": "#45B7D1",
           "董卓": "#45B7D1",
           "刘备": "#96CEB4",
           "张飞": "#96CEB4",
           "关羽": "#FF6B6B"
       },
       "search_keyword": "",
       "enable_hotkey": true,
       "enable_mouse": false
   }
   ```

## 打包说明

项目已提供 `build.spec`，可用于 PyInstaller 打包。常见打包方式如下：

```bash
pyinstaller build.spec
```

打包后请确保以下资源文件存在：
- 声音识别模型文件 `assets/models/yamnet.tflite`
- 图标文件 `laughter_can.ico`

## 依赖库

| 依赖包         | 用途            |
| -------------- | --------------- |
| PyQt6          | 桌面界面与交互  |
| pygame         | 音频播放        |
| sounddevice    | 麦克风音频采集  |
| numpy          | 音频数据处理    |
| keyboard       | 全局快捷键监听  |
| pynput         | 鼠标手势监听    |
| ai-edge-litert | TFLite 推理支持 |
| pyinstaller    | 打包 EXE        |

## 声明与开源许可证

**声明：本软件免费，禁止商用贩卖，使用代表同意自行承担所有后果。**

本项目采用 **[知识共享 署名 - 非商业性使用 - 相同方式共享 4.0 国际许可证 (CC BY-NC-SA 4.0)](LICENSE)** 授权。

### 核心条款说明

1. **允许的行为**：你可以自由复制、修改、分发本项目的代码 / 程序，前提是满足以下条件；
2. **禁止的行为**：严禁将本项目（包括修改后的衍生版本）用于任何商业目的（如出售、付费分发、商业运营等）；
3. **必须遵守**：
   - **署名**：必须保留原作者信息（[@依然匹萨吧](https://space.bilibili.com/6297797)）；
   - **相同方式共享**：若你修改 / 衍生本项目，必须采用与本协议相同的许可证发布。

请查看官方协议全文：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans

本项目仅供学习交流使用，禁止商用或贩卖。
