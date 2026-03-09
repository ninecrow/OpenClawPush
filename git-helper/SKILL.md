---
name: git-helper
description: |
  Git 版本控制助手。当用户提到 git、版本控制、提交代码、分支管理、代码合并等时触发。
  提供常用 Git 操作自动化、工作流管理、冲突解决辅助等功能。
  
  触发词：git、提交代码、创建分支、合并分支、代码冲突、版本控制
  
  功能：
  1. 常用 Git 命令快捷操作
  2. 分支管理自动化
  3. 提交规范检查
  4. 冲突解决辅助
  5. Git 工作流模板
---

# Git 助手

Git 版本控制助手，简化日常 Git 操作。

## 功能概览

1. **常用命令快捷操作** - 简化日常 Git 命令
2. **分支管理** - 创建、切换、合并分支
3. **提交规范** - 自动生成规范提交信息
4. **冲突解决** - 辅助解决合并冲突
5. **工作流模板** - Feature Branch、Git Flow 等

## 快速开始

### 查看 Git 状态
```bash
python scripts/git_commands.py status
```

### 创建新分支并切换
```bash
python scripts/git_workflow.py feature my-feature
```

### 规范提交
```bash
python scripts/git_commands.py commit "feat: 添加登录功能"
```

## 脚本说明

### git_commands.py

常用 Git 命令封装。

**功能**:
- `status` - 查看仓库状态
- `commit <message>` - 提交代码
- `push [branch]` - 推送到远程
- `pull` - 拉取最新代码
- `log [n]` - 查看提交历史
- `diff` - 查看改动

### git_workflow.py

Git 工作流管理。

**功能**:
- `feature <name>` - 创建 feature 分支
- `hotfix <name>` - 创建 hotfix 分支
- `release <version>` - 创建 release 分支
- `finish` - 完成当前分支并合并
- `sync` - 同步主分支

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `style:` 格式
- `refactor:` 重构
- `test:` 测试
- `chore:` 构建/工具

## 常用命令速查

参考: [references/git_cheatsheet.md](references/git_cheatsheet.md)
