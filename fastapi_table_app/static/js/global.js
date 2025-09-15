/**
 * グローバル設定・キーボードショートカット管理ファイル
 * キーボードショートカット、グローバル関数の公開、システム全体の設定を管理
 * アプリケーション全体に影響する設定とアクセシビリティ機能を含む
 */

// ==================== キーボードショートカット ====================
document.addEventListener('keydown', function(e) {
    // Ctrl + R でデータリフレッシュ
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        refreshData();
    }
    
    // Ctrl + F でフィルター適用
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        applyFilters();
    }
    
    // Escキーでモーダルを閉じる
    if (e.key === 'Escape') {
        closeVideoModal();
        closeModal();
    }
});

// ==================== グローバル関数として公開 ====================
window.refreshData = refreshData;
window.copyPath = copyPath;
window.showPathModal = showPathModal;
window.closeModal = closeModal;
window.playVideo = playVideo;
window.closeVideoModal = closeVideoModal;
window.applyFilters = applyFilters;
window.exportToCSV = exportToCSV;