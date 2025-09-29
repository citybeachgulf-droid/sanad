// Auto-initialize Simple-DataTables on tables marked with data-enhance="table"
document.addEventListener('DOMContentLoaded', function () {
  // Apply saved theme colors and logo from localStorage
  try {
    var theme = localStorage.getItem('app_theme');
    if (theme) {
      var cfg = JSON.parse(theme);
      var root = document.documentElement;
      Object.keys(cfg || {}).forEach(function (k) {
        if (k && cfg[k]) root.style.setProperty(k, cfg[k]);
      });
    }
    var logoUrl = localStorage.getItem('app_logo_url');
    var logoEl = document.getElementById('brandLogo');
    if (logoEl) {
      if (logoUrl) {
        logoEl.src = logoUrl;
        logoEl.classList.remove('d-none');
      } else {
        logoEl.classList.add('d-none');
      }
    }
  } catch (e) {}

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

  // Initialize Bootstrap toasts for flash messages
  try {
    document.querySelectorAll('.toast').forEach(function (el) {
      var t = new bootstrap.Toast(el);
      t.show();
    });
  } catch (e) {}

  // Table export utilities (CSV and Print)
  function tableToCSV(table) {
    const rows = Array.from(table.querySelectorAll('tr'));
    return rows.map(function (row) {
      const cols = Array.from(row.querySelectorAll('th,td'));
      return cols.map(function (cell) {
        const text = (cell.innerText || '').replace(/\s+/g, ' ').trim();
        const needsQuote = /[",\n]/.test(text);
        const escaped = '"' + text.replace(/"/g, '""') + '"';
        return needsQuote ? escaped : text;
      }).join(',');
    }).join('\n');
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime || 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  document.querySelectorAll('.js-export-csv').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const card = btn.closest('.card') || document;
      const table = card.querySelector('table');
      if (!table) return;
      const csv = tableToCSV(table);
      const filename = btn.getAttribute('data-filename') || 'export.csv';
      download(filename, csv, 'text/csv;charset=utf-8;');
    });
  });

  document.querySelectorAll('.js-export-print').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const card = btn.closest('.card') || document;
      const table = card.querySelector('table');
      if (!table) return;
      const win = window.open('', '_blank');
      const style = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.rtl.min.css">';
      win.document.write('<html dir="rtl" lang="ar"><head><title>Print</title>' + style + '</head><body>');
      win.document.write('<div class="container py-3">' + table.outerHTML + '</div>');
      win.document.write('</body></html>');
      win.document.close();
      win.focus();
      win.print();
      win.close();
    });
  });
});

