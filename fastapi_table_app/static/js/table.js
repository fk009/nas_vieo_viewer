/**
 * テーブル関連機能管理ファイル
 * テーブル行のクリック処理、統計情報の更新、表示件数の管理を含む
 * 行の選択状態とデータ表示の統計処理を管理
 */

// ==================== テーブル行クリック処理 ====================
function handleRowClick(event) {
    // ファイルパスセルがクリックされた場合は処理しない
    if (event.target.classList.contains('file-path-cell')) {
        return;
    }

    const row = event.currentTarget;
    const cells = row.querySelectorAll('td');

    // 現在選択されている行のハイライトを解除
    document.querySelectorAll('.data-table tbody tr').forEach(r => {
        r.classList.remove('selected');
    });

    // クリックした行をハイライト
    row.classList.add('selected');

    // 行のデータを取得
    const rowData = {
        id: cells[0]?.textContent,
        datetime: cells[1]?.textContent,
        option: cells[2]?.textContent,
        category: cells[3]?.textContent,
        filePath: cells[4]?.textContent,
        date: cells[5]?.textContent
    };

    console.log('選択された行:', rowData);
}

// ==================== 統計情報更新 ====================
function updateVisibleCount(count = null) {
    if (count === null) {
        const visibleRows = document.querySelectorAll('.data-table tbody tr:not([style*="display: none"])');
        count = visibleRows.length;
    }

    const visibleCountElement = document.getElementById('visible-count');
    if (visibleCountElement) {
        visibleCountElement.textContent = count;
    }
}

function updateStatistics() {
    const totalRows = document.querySelectorAll('.data-table tbody tr').length;
    const visibleRows = document.querySelectorAll('.data-table tbody tr:not([style*="display: none"])').length;

    const totalCountElement = document.getElementById('total-count');
    const visibleCountElement = document.getElementById('visible-count');

    if (totalCountElement) totalCountElement.textContent = totalRows;
    if (visibleCountElement) visibleCountElement.textContent = visibleRows;
}