# AI 助手 Alfred 工作流

这是一个基于 Gemini API 的 Alfred 工作流，可以帮助您快速获取 AI 回答。

![Alfred AI 工作流运行示例](snapshot.png)

## 功能

- 解释词义
- 翻译成英文
- 电影简介
- 自定义提示

## 系统要求

- Alfred 5.x 或更高版本
- Python 3.x 或更高版本

## 使用方法

1. 按下快捷键 `Cmd+Option+Ctrl+↓` 激活工作流
2. 选择提示模式
3. 输入您的问题
4. 查看 AI 回答

## 打包工作流

要打包成 Alfred 工作流文件(.alfredworkflow)，请执行以下步骤：

1. 确保您有执行权限：
```bash
chmod +x package.sh
```

2. 运行打包脚本：
```bash
./package.sh
```

3. 脚本会自动生成 `.alfredworkflow` 文件，文件名为 `[工作流名称]_v[版本号].alfredworkflow`

## 配置

在 Alfred 工作流设置中配置以下环境变量：
- `GEMINI_API_KEY_ALFRED`: 您的 Gemini API 密钥
- `CLASH_PROXY_URL`（可选）: 如果需要代理，例如 `http://127.0.0.1:7890`


## 许可证

MIT