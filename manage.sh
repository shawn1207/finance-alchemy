#!/bin/bash

# Configuration
REDIS_PORT=6379
CELERY_APP="src.tasks.celery_app"
GRADIO_APP="src.interface.gui.main"
VENV_PYTHON="./venv/bin/python"
VENV_CELERY="./venv/bin/celery"

# macOS Fork Compatibility Fix
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

function check_redis() {
    if ! redis-cli -p $REDIS_PORT ping > /dev/null 2>&1; then
        echo "⏳ Redis 未启动，正在尝试通过 brew services 启动..."
        if command -v brew >/dev/null 2>&1; then
            brew services start redis
            sleep 2
        else
            echo "❌ 错误: Redis 未运行且未找到 brew。请手动启动 Redis。"
            return 1
        fi
    fi
    echo "✅ Redis 已就绪。"
    return 0
}

function start() {
    echo "🚀 正在启动 Finance Alchemy 系统..."
    
    check_redis || exit 1

    # Start Celery
    echo "📦 正在启动 Celery Worker (Solo Pool)..."
    nohup $VENV_CELERY -A $CELERY_APP worker --loglevel=info --pool=solo > celery.log 2>&1 &
    CELERY_PID=$!
    echo $CELERY_PID > .celery.pid
    
    # Start Gradio
    echo "🖥️ 正在启动 Gradio GUI..."
    nohup $VENV_PYTHON -m $GRADIO_APP > gradio.log 2>&1 &
    GRADIO_PID=$!
    echo $GRADIO_PID > .gradio.pid

    echo "✨ 系统启动中！"
    echo "   - Celery 日志: tail -f celery.log"
    echo "   - Gradio 日志: tail -f gradio.log"
    echo "   - 访问地址: http://127.0.0.1:7860"
}

function stop() {
    echo "🛑 正在停止 Finance Alchemy 系统..."
    
    if [ -f .gradio.pid ]; then
        PID=$(cat .gradio.pid)
        echo "终止 Gradio (PID: $PID)..."
        kill $PID 2>/dev/null || pkill -f "$GRADIO_APP"
        rm .gradio.pid
    else
        pkill -f "$GRADIO_APP"
    fi

    if [ -f .celery.pid ]; then
        PID=$(cat .celery.pid)
        echo "终止 Celery (PID: $PID)..."
        kill $PID 2>/dev/null || pkill -f "celery"
        rm .celery.pid
    else
        pkill -f "celery"
    fi

    echo "✅ 所有服务已停止。"
}

function status() {
    echo "📊 服务状态检查:"
    
    # Redis
    if redis-cli -p $REDIS_PORT ping > /dev/null 2>&1; then
        echo "  - Redis:  🟢 运行中"
    else
        echo "  - Redis:  🔴 未运行"
    fi

    # Celery
    if pgrep -f "celery.*$CELERY_APP" > /dev/null; then
        echo "  - Celery: 🟢 运行中"
    else
        echo "  - Celery: 🔴 未运行"
    fi

    # Gradio
    if pgrep -f "$GRADIO_APP" > /dev/null; then
        echo "  - Gradio: 🟢 运行中"
    else
        echo "  - Gradio: 🔴 未运行"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
esac
