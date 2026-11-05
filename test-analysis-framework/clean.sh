#!/bin/bash
# 测试分析框架清理脚本
# 用于清理临时文件、输出文件或重置工作区

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"

WORKSPACE_DIR="$PROJECT_ROOT/workspace"
TMP_DIR="$WORKSPACE_DIR/tmp"
ROOT_TMP_DIR="$PROJECT_ROOT/tmp"
INPUT_DIR="$WORKSPACE_DIR/input/requirements"
TEST_POINTS_DIR="$WORKSPACE_DIR/output/test-points"
TEST_CASES_DIR="$WORKSPACE_DIR/output/test-cases"

ensure_directories() {
    mkdir -p "$TMP_DIR" "$ROOT_TMP_DIR" "$INPUT_DIR" "$TEST_POINTS_DIR" "$TEST_CASES_DIR"
}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示菜单
show_menu() {
    echo ""
    echo "=================================="
    echo "  测试分析框架清理脚本"
    echo "=================================="
    echo ""
    echo "请选择清理范围："
    echo ""
    echo "  1. 清理临时文件 (workspace/tmp/)"
    echo "  2. 清理测试点输出 (workspace/output/test-points/)"
    echo "  3. 清理测试用例输出 (workspace/output/test-cases/)"
    echo "  4. 清理所有输出文件 (test-points + test-cases)"
    echo "  5. 清理输入文件 (workspace/input/requirements/)"
    echo "  6. 完全重置工作区 (保留项目结构，清空所有数据)"
    echo "  7. 查看当前文件统计"
    echo "  0. 退出"
    echo ""
    echo "=================================="
}

# 统计文件
count_files() {
    echo ""
    echo -e "${GREEN}当前文件统计：${NC}"
    echo ""

    if [ -d "$PROJECT_ROOT/workspace/tmp" ]; then
        TMP_COUNT=$(find "$PROJECT_ROOT/workspace/tmp" -type f 2>/dev/null | wc -l)
        echo "  临时文件 (tmp/): $TMP_COUNT 个"
    fi

    if [ -d "$PROJECT_ROOT/workspace/output/test-points" ]; then
        TP_COUNT=$(find "$PROJECT_ROOT/workspace/output/test-points" -type f 2>/dev/null | wc -l)
        echo "  测试点文件 (test-points/): $TP_COUNT 个"
    fi

    if [ -d "$PROJECT_ROOT/workspace/output/test-cases" ]; then
        TC_COUNT=$(find "$PROJECT_ROOT/workspace/output/test-cases" -type f 2>/dev/null | wc -l)
        echo "  测试用例文件 (test-cases/): $TC_COUNT 个"
    fi

    if [ -d "$PROJECT_ROOT/workspace/input/requirements" ]; then
        REQ_COUNT=$(find "$PROJECT_ROOT/workspace/input/requirements" -type f 2>/dev/null | wc -l)
        echo "  需求文件 (requirements/): $REQ_COUNT 个"
    fi

    echo ""
}

# 清理临时文件
clean_tmp() {
    echo -e "${YELLOW}正在清理临时文件...${NC}"
    ensure_directories
    rm -rf "$TMP_DIR"/* "$ROOT_TMP_DIR"/*
    echo -e "${GREEN}✅ 临时文件清理完成${NC}"
}

# 清理测试点输出
clean_test_points() {
    echo -e "${YELLOW}正在清理测试点输出...${NC}"
    ensure_directories
    COUNT=$(find "$TEST_POINTS_DIR" -type f | wc -l)
    rm -rf "$TEST_POINTS_DIR"/*
    echo -e "${GREEN}✅ 已删除 $COUNT 个测试点文件${NC}"
}

# 清理测试用例输出
clean_test_cases() {
    echo -e "${YELLOW}正在清理测试用例输出...${NC}"
    ensure_directories
    COUNT=$(find "$TEST_CASES_DIR" -type f | wc -l)
    rm -rf "$TEST_CASES_DIR"/*
    echo -e "${GREEN}✅ 已删除 $COUNT 个测试用例文件${NC}"
}

# 清理所有输出文件
clean_all_output() {
    echo -e "${YELLOW}正在清理所有输出文件...${NC}"
    clean_test_points
    clean_test_cases
    clean_tmp
    echo -e "${GREEN}✅ 所有输出文件清理完成${NC}"
}

# 清理输入文件
clean_input() {
    echo -e "${RED}⚠️  警告：此操作将删除所有需求输入文件！${NC}"
    read -p "确定要继续吗？(yes/no): " confirm

    if [ "$(echo "$confirm" | tr '[:upper:]' '[:lower:]')" = "yes" ]; then
        ensure_directories
        COUNT=$(find "$INPUT_DIR" -type f | wc -l)
        rm -rf "$INPUT_DIR"/*
        echo -e "${GREEN}✅ 已删除 $COUNT 个需求文件${NC}"
    else
        echo -e "${YELLOW}❌ 取消清理${NC}"
    fi
}

# 完全重置工作区
reset_workspace() {
    echo -e "${RED}⚠️  警告：此操作将清空工作区的所有数据！${NC}"
    echo -e "${RED}     (保留目录结构，清空输入材料、输出产物、临时文件)${NC}"
    read -p "确定要继续吗？输入 'RESET' 确认: " confirm

    if [ "$(echo "$confirm" | tr '[:lower:]' '[:upper:]')" = "RESET" ]; then
        echo -e "${YELLOW}正在重置工作区...${NC}"
        ensure_directories

        # 清理所有文件（包括输入材料、输出产物、临时文件）
        rm -rf "$TMP_DIR"/*
        rm -rf "$TEST_POINTS_DIR"/*
        rm -rf "$TEST_CASES_DIR"/*
        rm -rf "$INPUT_DIR"/*
        rm -rf "$PROJECT_ROOT/workspace/.memory"/*

        # 同时清理项目根目录下的tmp目录
        rm -rf "$ROOT_TMP_DIR"/*

        # 创建 .gitkeep 文件保持目录结构
        touch "$TMP_DIR/.gitkeep" "$TEST_POINTS_DIR/.gitkeep" "$TEST_CASES_DIR/.gitkeep" "$INPUT_DIR/.gitkeep" "$ROOT_TMP_DIR/.gitkeep"

        echo -e "${GREEN}✅ 工作区重置完成${NC}"
        echo -e "${GREEN}   - 已清理输入材料 (input/requirements/)${NC}"
        echo -e "${GREEN}   - 已清理输出产物 (output/test-points/, output/test-cases/)${NC}"
        echo -e "${GREEN}   - 已清理临时文件 (workspace/tmp/, tmp/)${NC}"
    else
        echo -e "${YELLOW}❌ 取消重置${NC}"
    fi
}

# 主循环
main() {
    while true; do
        show_menu
        read -p "请输入选项 (0-7): " choice

        case $choice in
            1)
                clean_tmp
                ;;
            2)
                clean_test_points
                ;;
            3)
                clean_test_cases
                ;;
            4)
                clean_all_output
                ;;
            5)
                clean_input
                ;;
            6)
                reset_workspace
                ;;
            7)
                count_files
                ;;
            0)
                echo ""
                echo -e "${GREEN}退出清理脚本${NC}"
                echo ""
                exit 0
                ;;
            *)
                echo -e "${RED}❌ 无效选项，请重新选择${NC}"
                ;;
        esac

        echo ""
        read -p "按回车键继续..."
    done
}

# 执行主函数
main
