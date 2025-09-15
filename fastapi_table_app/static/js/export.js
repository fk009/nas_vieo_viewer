/**
 * エクスポート機能管理ファイル
 * データのCSVエクスポート、ファイルダウンロード機能を管理
 * テーブルデータの変換とファイル生成処理を含む
 */

// ==================== エクスポート機能（将来の拡張用） ====================
function exportToCSV() {
    const table = document.querySelector('.data-table');
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tr'));
    const csvContent = rows.map(row => {
        const cells = Array.from(row.querySelectorAll('th, td'));
        return cells.map(cell => `"${cell.textContent.trim()}"`).join(',');
    }).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `nas_data_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}