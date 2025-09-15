/**
 * ユーティリティ・通知機能管理ファイル
 * 汎用的なヘルパー関数、通知システム、パフォーマンス最適化関数を管理
 * debounce、throttle、通知表示機能を含む
 */

// ==================== 通知機能（改良版） ====================
function showNotification(message, type = 'success') {
    // 既存の通知を削除
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // 新しい通知を作成
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;

    const bgColors = {
        'success': '#28a745',
        'error': '#dc3545',
        'info': '#17a2b8',
        'warning': '#ffc107'
    };

    const bgColor = bgColors[type] || bgColors.success;
    const textColor = type === 'warning' ? '#212529' : 'white';

    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: ${bgColor};
        color: ${textColor};
        padding: 12px 20px;
        border-radius: 5px;
        z-index: 1000;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        animation: slideIn 0.3s ease-out;
        max-width: 300px;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.1);
        cursor: pointer;
    `;

    // クリックで手動削除
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    });

    document.body.appendChild(notification);

    // 自動削除（エラーは長めに表示）
    const deleteTime = type === 'error' ? 5000 : 3000;
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, deleteTime);
}

// ==================== ユーティリティ関数 ====================
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}