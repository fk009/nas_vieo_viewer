/**
 * 日時管理機能ファイル
 * 現在日時の表示更新、日時フォーマット処理を管理
 * リアルタイム時刻表示とフォーマット変換を含む
 */

// ==================== 日時更新機能 ====================
function updateDateTime() {
    const datetimeDisplay = document.querySelector('.datetime-display');
    if (datetimeDisplay) {
        const now = new Date();
        const formatted = formatDateTime(now);
        // リフレッシュボタンを除いた部分のみを更新
        const refreshBtn = datetimeDisplay.querySelector('.refresh-btn');
        const refreshBtnHTML = refreshBtn ? refreshBtn.outerHTML : '';
        datetimeDisplay.innerHTML = formatted + refreshBtnHTML;
    }
}

function formatDateTime(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');

    return `${year}年${month}月${day}日 ${hours}時${minutes}分`;
}