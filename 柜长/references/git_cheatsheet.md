# Git 速查表

## 常用命令

### 基础操作
```bash
# 克隆仓库
git clone <url>

# 查看状态
git status

# 添加文件
git add <file>           # 添加指定文件
git add .                # 添加所有改动

# 提交代码
git commit -m "message"
git commit -am "message" # 添加并提交

# 推送和拉取
git push                 # 推送到远程
git pull                 # 拉取最新代码
git fetch                # 获取远程分支（不合并）
```

### 分支操作
```bash
# 查看分支
git branch               # 本地分支
git branch -a            # 所有分支
git branch -r            # 远程分支

# 创建和切换
git branch <name>        # 创建分支
git checkout <name>      # 切换分支
git checkout -b <name>   # 创建并切换
git switch <name>        # 切换分支（新命令）
git switch -c <name>     # 创建并切换（新命令）

# 合并分支
git merge <branch>       # 合并指定分支到当前
git merge --abort        # 取消合并

# 删除分支
git branch -d <name>     # 删除已合并分支
git branch -D <name>     # 强制删除
```

### 查看历史
```bash
# 提交日志
git log
git log --oneline        # 简洁格式
git log --graph          # 图形化
git log -n 5             # 最近5条

# 查看改动
git diff                 # 工作区 vs 暂存区
git diff --cached        # 暂存区 vs 最新提交
git diff <commit>        # 与指定提交对比

# 查看某行代码的修改历史
git blame <file>
```

### 撤销操作
```bash
# 撤销工作区改动
git checkout -- <file>
git restore <file>       # 新命令

# 撤销暂存区
git reset HEAD <file>
git restore --staged <file>  # 新命令

# 修改最后一次提交
git commit --amend

# 回退到指定版本
git reset --hard <commit>
git reset --soft <commit>    # 保留改动
```

### 暂存操作
```bash
git stash                # 暂存当前改动
git stash push -m "msg"  # 带说明的暂存
git stash list           # 查看暂存列表
git stash pop            # 恢复并删除暂存
git stash apply          # 恢复但不删除
git stash drop           # 删除暂存
git stash clear          # 清空所有暂存
```

### 标签操作
```bash
git tag                          # 列出标签
git tag <name>                   # 创建标签
git tag -a <name> -m "msg"       # 创建附注标签
git push origin <tag>            # 推送标签
git push origin --tags           # 推送所有标签
git tag -d <name>                # 删除标签
```

### 远程操作
```bash
git remote -v                    # 查看远程地址
git remote add <name> <url>      # 添加远程
git remote remove <name>         # 删除远程
git remote set-url <name> <url>  # 修改远程地址
```

### 子模块
```bash
git submodule add <url> <path>   # 添加子模块
git submodule update --init      # 初始化和更新
git submodule update --remote    # 更新到最新
```

## 工作流

### Feature Branch 工作流
```bash
# 1. 从 main 创建 feature 分支
git checkout main
git pull
git checkout -b feature/my-feature

# 2. 开发并提交
git add .
git commit -m "feat: 添加新功能"

# 3. 推送到远程
git push -u origin feature/my-feature

# 4. 创建 PR 合并到 main

# 5. 清理
git checkout main
git pull
git branch -d feature/my-feature
```

### Hotfix 工作流
```bash
# 1. 从 main 创建 hotfix 分支
git checkout main
git pull
git checkout -b hotfix/fix-bug

# 2. 修复并提交
git commit -am "fix: 修复 bug"

# 3. 合并回 main
git checkout main
git merge hotfix/fix-bug
git push

# 4. 如有需要，合并到 develop
git checkout develop
git merge hotfix/fix-bug
```

## 提交规范 (Conventional Commits)

```
<type>(<scope>): <subject>

[body]

[footer]
```

### Type
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试
- `chore`: 构建/工具/依赖

### 示例
```
feat(user): 添加用户登录功能

fix(api): 修复接口返回错误

docs(readme): 更新安装说明

refactor(utils): 重构日期工具函数
```

## 解决冲突

当合并出现冲突时：

1. 打开冲突文件，找到冲突标记
```
<<<<<<< HEAD
当前分支的代码
=======
要合并的分支的代码
>>>>>>> branch-name
```

2. 手动编辑，保留需要的代码，删除标记

3. 标记为已解决
```bash
git add <file>
```

4. 完成合并
```bash
git commit
```

## 配置

```bash
# 全局配置
git config --global user.name "Your Name"
git config --global user.email "email@example.com"
git config --global core.editor "vim"
git config --global init.defaultBranch main

# 查看配置
git config --list
git config user.name
```

## 忽略文件 (.gitignore)

```gitignore
# 编译输出
*.exe
*.dll
*.so
build/
dist/

# 依赖
node_modules/
vendor/

# IDE
.idea/
.vscode/
*.swp

# 日志和临时文件
*.log
*.tmp
.DS_Store

# 环境变量
.env
.env.local
```
