# 贡献指南

感谢你对小红书自动发布系统的贡献！

## 如何贡献

### 提交Issue

- 描述问题时请提供详细信息
- 包括系统环境、Python版本、错误日志
- 如果是功能请求，请描述使用场景

### 提交代码

1. Fork本仓库
2. 创建你的功能分支：`git checkout -b feature/AmazingFeature`
3. 提交你的改动：`git commit -m 'Add some AmazingFeature'`
4. 推送到分支：`git push origin feature/AmazingFeature`
5. 提交Pull Request

## 代码规范

- 遵循PEP 8编码规范
- 添加必要的注释和文档
- 保持函数简洁，单一职责

## 测试

在提交PR前，请确保：

```bash
# 代码语法检查
python -m py_compile src/*.py

# 功能测试
python3 src/xiaohongshu_pause.py status
```

## 文档

更新相关的文档：
- README.md
- docs/目录下的文档
- 代码注释

## 发布流程

1. 更新版本号
2. 更新CHANGELOG.md
3. 打标签：`git tag v1.0.0`
4. 推送到GitHub：`git push origin v1.0.0`

## 联系方式

如有问题，请通过Issue联系。
