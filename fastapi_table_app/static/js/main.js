/**
 * メイン初期化処理ファイル
 * DOM読み込み完了後の処理と初期化関数を管理
 * アプリケーションの起点となる処理を含む
 */

// ==================== DOM読み込み完了後の処理 ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeFilters();
    updateDateTime();
    updateVisibleCount();

    // カテゴリセルのスタイル調整
    document.querySelectorAll('.category-cell').forEach(cell => {
        const text = cell.textContent.trim();
        if (text === 'エラー') {
            cell.style.fontWeight = 'bold';
            cell.style.letterSpacing = '0.5px';
        }
    });
});

// ==================== 初期化関数 ====================
function initializeEventListeners() {
    // 検索ボタンのクリックイベント
    const searchBtn = document.querySelector('.search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }

    // テーブル行のクリックイベント
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', handleRowClick);
    });

    // チェックボックスの変更イベント
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', debounce(applyFilters, 300));
    });

    // モーダル関連のイベント
    const pathModal = document.getElementById('pathModal');
    const videoModal = document.getElementById('videoModal');
    const span = document.getElementsByClassName('close')[0];

    // パスモーダルのクローズイベント
    if (span) {
        span.onclick = function() {
            pathModal.style.display = 'none';
        }
    }

    // ウィンドウクリックでモーダルを閉じる
    window.onclick = function(event) {
        if (event.target == pathModal) {
            pathModal.style.display = 'none';
        }
        if (event.target == videoModal) {
            closeVideoModal();
        }
    }
}

function initializeFilters() {
    // チェックボックスの初期状態を反映
    applyFilters();
}

// 日付・時間入力ボックスのクリア関数
function clearInput(id) {
    const input = document.getElementById(id);
    if (input) {
        input.value = '';
        // flatpickr対応
        if (input._flatpickr) {
            input._flatpickr.clear();
        }
    }
}