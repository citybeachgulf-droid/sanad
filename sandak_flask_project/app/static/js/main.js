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

  // Auto-open filters on large screens, keep collapsed on mobile for a cleaner UI
  try {
    var filters = document.getElementById('filtersCollapse');
    if (filters) {
      if (window.matchMedia('(min-width: 992px)').matches) {
        new bootstrap.Collapse(filters, { toggle: false }).show();
      }
    }
  } catch (e) {}
});

