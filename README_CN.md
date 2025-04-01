# Reddit 数据处理工具

## 项目简介
这是一个用于处理Reddit数据的工具，支持数据获取、翻译、分析和报告生成功能。

## 环境配置

1. 克隆仓库
```bash
git clone <repository-url>
cd reddit
```

2. 安装Python依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
复制.env.example文件并重命名为.env，然后编辑其中的配置项：
```
REDDIT_CLIENT_ID=你的Reddit客户端ID
REDDIT_CLIENT_SECRET=你的Reddit客户端密钥
REDDIT_USER_AGENT=你的Reddit用户代理

TRANSLATION_ACCESS_KEY_ID=阿里云翻译API访问密钥ID
TRANSLATION_ACCESS_KEY_SECRET=阿里云翻译API访问密钥
TRANSLATION_ENABLED=是否启用翻译功能(true/false)

LLM_API_KEY=大语言模型API密钥
LLM_MODEL_NAME=使用的大语言模型名称
LLM_BASE_URL=大语言模型API基础URL

MD_TO_IMAGE=是否启用Markdown转图片功能(true/false)
```

## 使用方法
1. 确保所有依赖已安装
2. 正确配置.env文件
3. 运行主程序
```bash
python main.py
```

## 注意事项
1. 如需使用Markdown转图片功能(MD_TO_IMAGE=true)，必须安装wkhtmltopdf
   - 请访问 https://wkhtmltopdf.org/ 下载并安装对应版本的wkhtmltopdf
   - 确保wkhtmltopdf可执行文件路径已添加到系统PATH环境变量中

2. 翻译功能需要有效的阿里云翻译API密钥

3. 大语言模型功能需要配置正确的API密钥和模型名称