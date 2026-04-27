@echo off
REM E2E 测试快速启动脚本 (Windows)
REM 用法: run-e2e-tests.bat [test-file]

echo 🚀 启动 E2E 测试环境...
echo.

REM 检查 Mock Server 是否运行
curl -s http://localhost:8797/rest/api/3/myself >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Mock Jira Server 运行中 (端口 8797)
    set MOCK_RUNNING=1
) else (
    echo ✗ Mock Jira Server 未运行
    set MOCK_RUNNING=0
)

REM 检查前端是否运行
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 前端应用运行中 (端口 5173)
    set FRONTEND_RUNNING=1
) else (
    echo ✗ 前端应用未运行
    set FRONTEND_RUNNING=0
)

echo.

REM 启动 Mock Server (如果未运行)
if %MOCK_RUNNING% equ 0 (
    echo 启动 Mock Server...
    start /B npm run mock-server
    timeout /t 3 /nobreak >nul
    echo ✓ Mock Server 已启动
    echo.
)

REM 提示启动前端 (如果未运行)
if %FRONTEND_RUNNING% equ 0 (
    echo ⚠ 前端应用未运行
    echo   请在另一个终端运行: npm run dev
    echo.
    pause
)

echo 🧪 运行测试...
echo.

REM 运行测试
if "%~1"=="" (
    npx playwright test --reporter=list
) else (
    npx playwright test %1 --reporter=list
)

set TEST_EXIT_CODE=%errorlevel%

echo.
echo 📊 测试完成
echo.

if %TEST_EXIT_CODE% equ 0 (
    echo ✓ 所有测试通过
    echo.
    echo 查看详细报告:
    echo   npx playwright show-report
) else (
    echo ✗ 部分测试失败
    echo.
    echo 查看失败详情:
    echo   npx playwright show-report
)

exit /b %TEST_EXIT_CODE%
