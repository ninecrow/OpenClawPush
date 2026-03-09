"""
常用 Git 命令封装
简化日常 Git 操作
"""
import subprocess
import sys
import os
from typing import List, Optional, Tuple


def run_git_command(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    """
    执行 Git 命令
    
    Args:
        args: Git 命令参数
        cwd: 工作目录
    
    Returns:
        (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def git_status() -> str:
    """查看 Git 状态"""
    code, stdout, stderr = run_git_command(['status'])
    if code == 0:
        return stdout
    return f"错误: {stderr}"


def git_add(files: Optional[List[str]] = None) -> bool:
    """
    添加文件到暂存区
    
    Args:
        files: 文件列表，None 表示添加所有
    """
    if files:
        code, _, stderr = run_git_command(['add'] + files)
    else:
        code, _, stderr = run_git_command(['add', '.'])
    
    if code != 0:
        print(f"添加失败: {stderr}")
        return False
    return True


def git_commit(message: str) -> bool:
    """
    提交代码
    
    Args:
        message: 提交信息
    """
    code, _, stderr = run_git_command(['commit', '-m', message])
    if code != 0:
        print(f"提交失败: {stderr}")
        return False
    print(f"✓ 提交成功: {message}")
    return True


def git_push(branch: Optional[str] = None) -> bool:
    """
    推送到远程
    
    Args:
        branch: 分支名，None 表示当前分支
    """
    if branch:
        code, _, stderr = run_git_command(['push', 'origin', branch])
    else:
        code, _, stderr = run_git_command(['push'])
    
    if code != 0:
        print(f"推送失败: {stderr}")
        return False
    print("✓ 推送成功")
    return True


def git_pull() -> bool:
    """拉取最新代码"""
    code, _, stderr = run_git_command(['pull'])
    if code != 0:
        print(f"拉取失败: {stderr}")
        return False
    print("✓ 拉取成功")
    return True


def git_log(n: int = 10) -> str:
    """
    查看提交历史
    
    Args:
        n: 显示最近 n 条
    """
    code, stdout, _ = run_git_command([
        'log', f'-{n}',
        '--oneline',
        '--graph',
        '--decorate',
        '--all'
    ])
    return stdout if code == 0 else "获取历史失败"


def git_diff() -> str:
    """查看改动"""
    code, stdout, _ = run_git_command(['diff'])
    return stdout if code == 0 else "获取 diff 失败"


def git_branch() -> str:
    """查看分支"""
    code, stdout, _ = run_git_command(['branch', '-a'])
    return stdout if code == 0 else "获取分支失败"


def git_checkout(branch: str, create: bool = False) -> bool:
    """
    切换分支
    
    Args:
        branch: 分支名
        create: 是否创建新分支
    """
    if create:
        code, _, stderr = run_git_command(['checkout', '-b', branch])
    else:
        code, _, stderr = run_git_command(['checkout', branch])
    
    if code != 0:
        print(f"切换分支失败: {stderr}")
        return False
    print(f"✓ 已切换到分支: {branch}")
    return True


def git_merge(branch: str) -> bool:
    """
    合并分支
    
    Args:
        branch: 要合并的分支
    """
    code, _, stderr = run_git_command(['merge', branch])
    if code != 0:
        print(f"合并失败: {stderr}")
        return False
    print(f"✓ 合并成功: {branch}")
    return True


def git_stash(message: Optional[str] = None) -> bool:
    """
    暂存改动
    
    Args:
        message: 暂存信息
    """
    if message:
        code, _, stderr = run_git_command(['stash', 'push', '-m', message])
    else:
        code, _, stderr = run_git_command(['stash'])
    
    if code != 0:
        print(f"暂存失败: {stderr}")
        return False
    print("✓ 已暂存改动")
    return True


def git_stash_pop() -> bool:
    """恢复暂存"""
    code, _, stderr = run_git_command(['stash', 'pop'])
    if code != 0:
        print(f"恢复失败: {stderr}")
        return False
    print("✓ 已恢复暂存")
    return True


def get_current_branch() -> str:
    """获取当前分支名"""
    code, stdout, _ = run_git_command(['branch', '--show-current'])
    return stdout.strip() if code == 0 else "unknown"


def has_uncommitted_changes() -> bool:
    """检查是否有未提交的改动"""
    code, stdout, _ = run_git_command(['status', '--porcelain'])
    return len(stdout.strip()) > 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Git 命令助手")
        print("\n用法: python git_commands.py <command> [args...]")
        print("\n命令:")
        print("  status              查看状态")
        print("  add [files...]      添加文件")
        print("  commit <msg>       提交代码")
        print("  push [branch]       推送到远程")
        print("  pull                拉取代码")
        print("  log [n]             查看历史")
        print("  diff                查看改动")
        print("  branch              查看分支")
        print("  checkout <branch>  切换分支")
        print("  merge <branch>     合并分支")
        print("  stash [message]     暂存改动")
        print("  stash-pop           恢复暂存")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        print(git_status())
    elif command == "add":
        files = sys.argv[2:] if len(sys.argv) > 2 else None
        git_add(files)
    elif command == "commit":
        if len(sys.argv) < 3:
            print("错误: 请提供提交信息")
            sys.exit(1)
        git_commit(sys.argv[2])
    elif command == "push":
        branch = sys.argv[2] if len(sys.argv) > 2 else None
        git_push(branch)
    elif command == "pull":
        git_pull()
    elif command == "log":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(git_log(n))
    elif command == "diff":
        print(git_diff())
    elif command == "branch":
        print(git_branch())
    elif command == "checkout":
        if len(sys.argv) < 3:
            print("错误: 请提供分支名")
            sys.exit(1)
        git_checkout(sys.argv[2])
    elif command == "merge":
        if len(sys.argv) < 3:
            print("错误: 请提供分支名")
            sys.exit(1)
        git_merge(sys.argv[2])
    elif command == "stash":
        message = sys.argv[2] if len(sys.argv) > 2 else None
        git_stash(message)
    elif command == "stash-pop":
        git_stash_pop()
    else:
        print(f"未知命令: {command}")
