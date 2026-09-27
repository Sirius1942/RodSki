#!/usr/bin/env python3
"""
macOS 系统性能监控脚本
检查 CPU、内存、磁盘、网络和进程状态
"""

import subprocess
import json
import os
from datetime import datetime

def run_command(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return f"错误: {str(e)}"

def get_cpu_info():
    """获取 CPU 信息"""
    print("\n" + "="*60)
    print("CPU 使用情况")
    print("="*60)

    # CPU 核心数
    cores = run_command("sysctl -n hw.ncpu")
    print(f"CPU 核心数: {cores}")

    # CPU 使用率（top 命令）
    cpu_usage = run_command("top -l 1 -n 0 | grep 'CPU usage'")
    print(f"CPU 使用率: {cpu_usage}")

    # 系统负载
    load = run_command("sysctl -n vm.loadavg")
    print(f"系统负载 (1/5/15分钟): {load}")

    # CPU 占用最高的进程
    print("\nCPU 占用 Top 10 进程:")
    top_cpu = run_command("ps aux | sort -nrk 3,3 | head -n 11 | tail -n 10")
    print(top_cpu)

def get_memory_info():
    """获取内存信息"""
    print("\n" + "="*60)
    print("内存使用情况")
    print("="*60)

    # 物理内存总量
    total_mem = run_command("sysctl -n hw.memsize")
    total_mem_gb = int(total_mem) / (1024**3)
    print(f"物理内存总量: {total_mem_gb:.2f} GB")

    # vm_stat 内存统计
    vm_stat = run_command("vm_stat")
    print(f"\n{vm_stat}")

    # 内存压力
    memory_pressure = run_command("memory_pressure 2>&1 | head -n 5")
    print(f"\n内存压力:\n{memory_pressure}")

    # 内存占用最高的进程
    print("\n内存占用 Top 10 进程:")
    top_mem = run_command("ps aux | sort -nrk 4,4 | head -n 11 | tail -n 10")
    print(top_mem)

def get_disk_info():
    """获取磁盘信息"""
    print("\n" + "="*60)
    print("磁盘使用情况")
    print("="*60)

    # 磁盘空间
    df = run_command("df -h /")
    print(f"根分区空间:\n{df}")

    # 磁盘 I/O 活动
    print("\n磁盘 I/O 统计:")
    iostat = run_command("iostat -d -c 2")
    print(iostat)

def get_network_info():
    """获取网络信息"""
    print("\n" + "="*60)
    print("网络状态")
    print("="*60)

    # 网络接口
    ifconfig = run_command("ifconfig | grep -E '^[a-z]|inet '")
    print(f"网络接口:\n{ifconfig}")

    # 活跃连接数
    connections = run_command("netstat -an | grep ESTABLISHED | wc -l")
    print(f"\n当前 ESTABLISHED 连接数: {connections}")

    # 网络流量 Top 进程
    print("\n网络占用 Top 进程:")
    nettop = run_command("nettop -P -L 1 -n -x 2>&1 | head -n 15")
    if "nettop" not in nettop and "command not found" not in nettop:
        print(nettop)
    else:
        print("(需要 root 权限或 nettop 不可用)")

def get_process_info():
    """获取进程信息"""
    print("\n" + "="*60)
    print("进程状态")
    print("="*60)

    # 进程总数
    proc_count = run_command("ps aux | wc -l")
    print(f"当前进程总数: {proc_count}")

    # 僵尸进程
    zombie = run_command("ps aux | grep -i defunct | grep -v grep | wc -l")
    print(f"僵尸进程数: {zombie}")

    # 线程数
    threads = run_command("ps -M | wc -l")
    print(f"线程总数: {threads}")

def get_swap_info():
    """获取交换空间信息"""
    print("\n" + "="*60)
    print("交换空间 (Swap)")
    print("="*60)

    swap = run_command("sysctl vm.swapusage")
    print(swap)

def check_hot_processes():
    """检查可能导致卡顿的热点进程"""
    print("\n" + "="*60)
    print("卡顿诊断 - 热点进程分析")
    print("="*60)

    # 检查高 CPU 进程（超过 50%）
    high_cpu = run_command("ps aux | awk '$3 > 50.0 {print $0}'")
    if high_cpu:
        print("\n⚠️  高 CPU 占用进程 (>50%):")
        print(high_cpu)
    else:
        print("\n✓ 无高 CPU 占用进程")

    # 检查高内存进程（超过 5%）
    high_mem = run_command("ps aux | awk '$4 > 5.0 {print $0}'")
    if high_mem:
        print("\n⚠️  高内存占用进程 (>5%):")
        print(high_mem)
    else:
        print("\n✓ 无异常高内存占用进程")

    # 检查 D 状态进程（不可中断睡眠，通常等待 I/O）
    d_state = run_command("ps aux | awk '$8 ~ /D/ {print $0}'")
    if d_state:
        print("\n⚠️  D 状态进程 (等待 I/O):")
        print(d_state)
    else:
        print("\n✓ 无 D 状态进程")

def main():
    print("="*60)
    print(f"macOS 系统性能监控报告")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    get_cpu_info()
    get_memory_info()
    get_swap_info()
    get_disk_info()
    get_network_info()
    get_process_info()
    check_hot_processes()

    print("\n" + "="*60)
    print("监控完成")
    print("="*60)

if __name__ == "__main__":
    main()
