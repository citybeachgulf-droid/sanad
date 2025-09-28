// Auto-initialize Simple-DataTables on tables marked with data-enhance="table"
document.addEventListener('DOMContentLoaded', function () {
  try {
    if (window.simpleDatatables) {
      document.querySelectorAll('table[data-enhance="table"]').forEach(function (tbl) {
        const options = {
          searchable: true,
          fixedHeight: true,
          labels: {
            placeholder: 'بحث...',
            perPage: '{select} لكل صفحة',
            noRows: 'لا توجد بيانات',
            info: 'إظهار {start} إلى {end} من {rows} صف'
          }
        };
        new simpleDatatables.DataTable(tbl, options);
      });
    }
  } catch (e) {
    // swallow errors to avoid breaking pages
    console && console.warn && console.warn('datatable init error', e);
  }
});

