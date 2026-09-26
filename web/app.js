let currentStatusFilter = 'all';

async function fetchOverview() {
  try {
    const res = await fetch('/api/overview');
    if (!res.ok) throw new Error('Failed to load overview data');
    const data = await res.json();

    document.getElementById('totalInvoices').textContent = data.summary.invoice_count;
    document.getElementById('openInvoices').textContent = data.summary.open_count;
    document.getElementById('totalOutstanding').textContent = '₹ ' + data.summary.outstanding.toFixed(2);

    renderUnmatched(data.unmatched_payments || []);
    fetchInvoices(currentStatusFilter);
  } catch (err) {
    console.error('Error fetching overview:', err);
  }
}

async function fetchInvoices(status = 'all') {
  currentStatusFilter = status;
  try {
    const res = await fetch(`/api/invoices?status=${status}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.error || 'Failed to load invoices');
    }
    const invoices = await res.json();
    renderInvoices(invoices);
  } catch (err) {
    const tbody = document.getElementById('invoicesBody');
    tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="color:red;">Error: ${err.message}</td></tr>`;
  }
}

function renderInvoices(invoices) {
  const tbody = document.getElementById('invoicesBody');
  if (invoices.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center">No invoices found.</td></tr>';
    return;
  }

  tbody.innerHTML = invoices.map(inv => `
    <tr>
      <td>${inv.id}</td>
      <td><strong>${inv.customer_id}</strong> <br><small style="color:#64748b">${inv.customer_name || ''}</small></td>
      <td>${inv.invoice_number}</td>
      <td>₹ ${Number(inv.amount).toFixed(2)}</td>
      <td>${inv.due_date}</td>
      <td>₹ ${Number(inv.paid).toFixed(2)}</td>
      <td>₹ ${Number(inv.balance).toFixed(2)}</td>
      <td>
        <span class="status-badge status-${inv.status}">${inv.status}</span>
      </td>
    </tr>
  `).join('');
}

function renderUnmatched(payments) {
  const countEl = document.getElementById('unmatchedCount');
  const tbody = document.getElementById('unmatchedBody');
  countEl.textContent = payments.length;

  if (payments.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">No unmatched payments.</td></tr>';
    return;
  }

  tbody.innerHTML = payments.map(p => `
    <tr>
      <td><strong>${p.payment_id}</strong></td>
      <td>${p.customer_id}</td>
      <td>${p.invoice_number}</td>
      <td>₹ ${Number(p.amount).toFixed(2)}</td>
    </tr>
  `).join('');
}

async function handleImport(kind, textContent, feedbackEl) {
  feedbackEl.className = 'feedback';
  feedbackEl.innerHTML = 'Importing...';

  try {
    const res = await fetch(`/api/import?kind=${kind}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'text/csv'
      },
      body: textContent
    });

    const data = await res.json();
    if (!res.ok) {
      feedbackEl.className = 'feedback feedback-error';
      feedbackEl.innerHTML = `<strong>Error:</strong> ${data.error || 'Import failed'}`;
      return;
    }

    // Refresh register after a processed import so records agree
    await fetchOverview();

    let html = `<strong>Import results:</strong> ${data.imported} imported, ${data.skipped} skipped, ${data.rejected} rejected.`;
    if (data.errors && data.errors.length > 0) {
      html += `<ul class="feedback-errors-list">` +
        data.errors.map(e => `<li>Line ${e.line}: ${e.reason}</li>`).join('') +
        `</ul>`;
      feedbackEl.className = 'feedback feedback-warning';
    } else {
      feedbackEl.className = 'feedback feedback-success';
    }
    feedbackEl.innerHTML = html;
  } catch (err) {
    feedbackEl.className = 'feedback feedback-error';
    feedbackEl.innerHTML = `<strong>Network error:</strong> ${err.message}`;
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  fetchOverview();

  // Filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      fetchInvoices(btn.dataset.status);
    });
  });

  // Invoice import
  const btnImportInvoices = document.getElementById('btnImportInvoices');
  const invoiceText = document.getElementById('invoiceCsv');
  const invoiceFileInput = document.getElementById('invoiceFileInput');
  const invoiceFeedback = document.getElementById('invoiceFeedback');

  invoiceFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => { invoiceText.value = evt.target.result; };
      reader.readAsText(file);
    }
  });

  btnImportInvoices.addEventListener('click', () => {
    const text = invoiceText.value.trim();
    if (!text) {
      invoiceFeedback.className = 'feedback feedback-error';
      invoiceFeedback.innerHTML = 'Please paste CSV content or select a file.';
      return;
    }
    handleImport('invoices', text, invoiceFeedback);
  });

  // Payment import
  const btnImportPayments = document.getElementById('btnImportPayments');
  const paymentText = document.getElementById('paymentCsv');
  const paymentFileInput = document.getElementById('paymentFileInput');
  const paymentFeedback = document.getElementById('paymentFeedback');

  paymentFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => { paymentText.value = evt.target.result; };
      reader.readAsText(file);
    }
  });

  btnImportPayments.addEventListener('click', () => {
    const text = paymentText.value.trim();
    if (!text) {
      paymentFeedback.className = 'feedback feedback-error';
      paymentFeedback.innerHTML = 'Please paste CSV content or select a file.';
      return;
    }
    handleImport('payments', text, paymentFeedback);
  });
});
