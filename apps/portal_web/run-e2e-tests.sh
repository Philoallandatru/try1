#!/bin/bash

# E2E 测试快速启动脚本
# 用法: ./run-e2e-tests.sh [test-file]

set -e

echo "🚀 启动 E2E 测试环境..."
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Mock Server 是否运行
check_mock_server() {
    if curl -s http://localhost:8797/rest/api/3/myself > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Mock Jira Server 运行中 (端口 8797)"
        return 0
    else
        echo -e "${RED}✗${NC} Mock Jira Server 未运行"
        return 1
    fi
}

# 检查前端是否运行
check_frontend() {
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 前端应用运行中 (端口 5173)"
        return 0
    else
        echo -e "${RED}✗${NC} 前端应用未运行"
        return 1
    fi
}

# 启动 Mock Server
start_mock_server() {
    echo -e "${YELLOW}启动 Mock Server...${NC}"
    npm run mock-server > /tmp/mock-server.log 2>&1 &
    MOCK_PID=$!
    sleep 3

    if check_mock_server; then
        echo -e "${GREEN}✓${NC} Mock Server 启动成功 (PID: $MOCK_PID)"
        echo $MOCK_PID > /tmp/mock-server.pid
    else
        echo -e "${RED}✗${NC} Mock Server 启动失败"
        cat /tmp/mock-server.log
        exit 1
    fi
}

# 主流程
main() {
    echo "📋 检查服务状态..."
    echo ""

    # 检查 Mock Server
    if ! check_mock_server; then
        start_mock_server
    fi

    # 检查前端
    if ! check_frontend; then
        echo -e "${YELLOW}⚠${NC}  前端应用未运行"
        echo "   请在另一个终端运行: npm run dev"
        echo ""
        read -p "前端启动后按 Enter 继续..."
    fi

    echo ""
    echo "🧪 运行测试..."
    echo ""

    # 运行测试
    if [ -z "$1" ]; then
        # 运行所有测试
        npx playwright test --reporter=list
    else
        # 运行指定测试
        npx playwright test "$1" --reporter=list
    fi

    TEST_EXIT_CODE=$?

    echo ""
    echo "📊 测试完成"
    echo ""

    # 显示报告
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓${NC} 所有测试通过"
        echo ""
        echo "查看详细报告:"
        echo "  npx playwright show-report"
    else
        echo -e "${RED}✗${NC} 部分测试失败"
        echo ""
        echo "查看失败详情:"
        echo "  npx playwright show-report"
    fi

    exit $TEST_EXIT_CODE
}

# 清理函数
cleanup() {
    echo ""
    echo "🧹 清理资源..."

    if [ -f /tmp/mock-server.pid ]; then
        MOCK_PID=$(cat /tmp/mock-server.pid)
        if kill -0 $MOCK_PID 2>/dev/null; then
            echo "停止 Mock Server (PID: $MOCK_PID)"
            kill $MOCK_PID
        fi
        rm /tmp/mock-server.pid
    fi
}

# 注册清理函数
trap cleanup EXIT

# 运行主流程
main "$@"
