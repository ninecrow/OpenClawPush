"""
Git 工作流管理
支持 Feature Branch、Hotfix、Release 等流程
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_commands import (
    run_git_command, git_checkout, git_pull, git_push,
    git_merge, get_current_branch, has_uncommitted_changes,
    git_stash, git_stash_pop
)


class GitWorkflow:
    """Git 工作流管理器"""
    
    def __init__(self, main_branch: str = "main"):
        self.main_branch = main_branch
    
    def _check_clean_workspace(self) -> bool:
        """检查工作区是否干净"""
        if has_uncommitted_changes():
            print("⚠️  工作区有未提交的改动")
            print("请先提交或暂存改动")
            return False
        return True
    
    def start_feature(self, feature_name: str) -> bool:
        """
        创建 feature 分支
        
        Args:
            feature_name: 功能名称
        """
        if not self._check_clean_workspace():
            return False
        
        branch_name = f"feature/{feature_name}"
        
        # 切换到主分支并拉取最新代码
        print(f"📥 同步 {self.main_branch} 分支...")
        git_checkout(self.main_branch)
        git_pull()
        
        # 创建并切换到 feature 分支
        print(f"🌿 创建分支: {branch_name}")
        git_checkout(branch_name, create=True)
        
        print(f"✓ Feature 分支创建成功: {branch_name}")
        print(f"\n开始开发功能: {feature_name}")
        return True
    
    def start_hotfix(self, hotfix_name: str) -> bool:
        """
        创建 hotfix 分支
        
        Args:
            hotfix_name: 修复名称
        """
        if not self._check_clean_workspace():
            return False
        
        branch_name = f"hotfix/{hotfix_name}"
        
        # 从主分支创建
        git_checkout(self.main_branch)
        git_pull()
        
        print(f"🔧 创建 Hotfix 分支: {branch_name}")
        git_checkout(branch_name, create=True)
        
        return True
    
    def start_release(self, version: str) -> bool:
        """
        创建 release 分支
        
        Args:
            version: 版本号，如 "v1.2.0"
        """
        if not self._check_clean_workspace():
            return False
        
        branch_name = f"release/{version}"
        
        git_checkout(self.main_branch)
        git_pull()
        
        print(f"🏷️  创建 Release 分支: {branch_name}")
        git_checkout(branch_name, create=True)
        
        return True
    
    def finish_feature(self) -> bool:
        """完成 feature 分支并合并到主分支"""
        current = get_current_branch()
        
        if not current.startswith("feature/"):
            print(f"⚠️  当前不在 feature 分支 (当前: {current})")
            return False
        
        if not self._check_clean_workspace():
            return False
        
        # 推送当前分支
        print(f"📤 推送分支: {current}")
        git_push(current)
        
        # 切换回主分支并合并
        print(f"🔀 合并到 {self.main_branch}...")
        git_checkout(self.main_branch)
        git_pull()
        
        if not git_merge(current):
            print("⚠️  合并出现冲突，请手动解决")
            return False
        
        # 推送主分支
        git_push(self.main_branch)
        
        # 删除 feature 分支
        print(f"🗑️  删除分支: {current}")
        run_git_command(['branch', '-d', current])
        
        print(f"✓ Feature 完成: {current}")
        return True
    
    def sync_with_main(self) -> bool:
        """同步主分支最新代码到当前分支"""
        current = get_current_branch()
        
        if current == self.main_branch:
            print("已经在主分支，直接拉取...")
            return git_pull()
        
        # 暂存当前改动
        has_changes = has_uncommitted_changes()
        if has_changes:
            print("📦 暂存当前改动...")
            git_stash("sync with main")
        
        # 切换到主分支并拉取
        git_checkout(self.main_branch)
        git_pull()
        
        # 切回原分支并合并
        git_checkout(current)
        print(f"🔀 合并 {self.main_branch} 到 {current}...")
        
        if not git_merge(self.main_branch):
            print("⚠️  合并出现冲突")
            return False
        
        # 恢复暂存
        if has_changes:
            print("📦 恢复暂存改动...")
            git_stash_pop()
        
        print(f"✓ 同步完成")
        return True
    
    def abort_merge(self) -> bool:
        """取消合并"""
        code, _, stderr = run_git_command(['merge', '--abort'])
        if code != 0:
            print(f"取消失败: {stderr}")
            return False
        print("✓ 已取消合并")
        return True


def print_help():
    """打印帮助信息"""
    print("""Git 工作流管理

用法: python git_workflow.py <command> [args...]

命令:
  feature <name>      创建 feature 分支
  hotfix <name>       创建 hotfix 分支
  release <version>   创建 release 分支
  finish               完成当前 feature 并合并
  sync                 同步主分支到当前分支
  abort-merge          取消当前合并

示例:
  python git_workflow.py feature login-page
  python git_workflow.py finish
  python git_workflow.py sync
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    workflow = GitWorkflow()
    command = sys.argv[1]
    
    if command == "feature":
        if len(sys.argv) < 3:
            print("错误: 请提供功能名称")
            sys.exit(1)
        workflow.start_feature(sys.argv[2])
    
    elif command == "hotfix":
        if len(sys.argv) < 3:
            print("错误: 请提供修复名称")
            sys.exit(1)
        workflow.start_hotfix(sys.argv[2])
    
    elif command == "release":
        if len(sys.argv) < 3:
            print("错误: 请提供版本号")
            sys.exit(1)
        workflow.start_release(sys.argv[2])
    
    elif command == "finish":
        workflow.finish_feature()
    
    elif command == "sync":
        workflow.sync_with_main()
    
    elif command == "abort-merge":
        workflow.abort_merge()
    
    else:
        print(f"未知命令: {command}")
        print_help()
