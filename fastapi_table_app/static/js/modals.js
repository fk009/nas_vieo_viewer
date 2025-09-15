/**
 * モーダル機能管理ファイル
 * パス表示モーダル、コピー機能、モーダルの開閉処理を管理
 * クリップボード操作とフォールバック処理を含む
 */

// ==================== モーダル機能（パス表示用） ====================
function showPathModal(filePath) {
    const modal = document.getElementById('pathModal');
    const pathElement = document.getElementById('modal-path');

    if (pathElement) {
        pathElement.textContent = filePath;
    }

    if (modal) {
        modal.style.display = 'block';
    }
}

function copyPath() {
    const pathElement = document.getElementById('modal-path');
    if (!pathElement) return;

    const pathText = pathElement.textContent;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(pathText).then(() => {
            showNotification('パスをクリップボードにコピーしました');
            closeModal();
        }).catch(err => {
            console.error('クリップボードコピー失敗:', err);
            fallbackCopyText(pathText);
        });
    } else {
        fallbackCopyText(pathText);
    }
}

function fallbackCopyText(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        showNotification('パスをクリップボードにコピーしました');
        closeModal();
    } catch (err) {
        console.error('フォールバックコピー失敗:', err);
        showNotification('コピーに失敗しました', 'error');
    }

    document.body.removeChild(textArea);
}

function closeModal() {
    const modal = document.getElementById('pathModal');
    if (modal) {
        modal.style.display = 'none';
    }
}