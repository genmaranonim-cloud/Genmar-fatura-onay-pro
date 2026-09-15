/* GENMAR Fatura Onay Pro - manuel fatura gezinme davranışı (CA)
   Onay işlemi sonraki faturaya otomatik geçmez.
*/
(() => {
  let approvalInProgress = false;

  window.genmarApprove = async function genmarApprove(invoiceId, payload = {}) {
    if (approvalInProgress) return;
    approvalInProgress = true;
    try {
      const response = await fetch(`/api/faturalar/${invoiceId}/onayla`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Onay işlemi başarısız.');

      // Bilerek nextInvoice() çağrılmıyor. Kullanıcı aynı faturada kalır.
      document.dispatchEvent(new CustomEvent('genmar:invoice-approved', {detail: result}));
      if (typeof window.refreshCurrentInvoice === 'function') {
        await window.refreshCurrentInvoice({showStampedPdf: true, readonly: true});
      }
      return result;
    } finally {
      approvalInProgress = false;
    }
  };

  document.addEventListener('keydown', (event) => {
    const tag = (event.target && event.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;
    if (event.key === 'ArrowRight' && typeof window.nextInvoice === 'function') {
      event.preventDefault();
      window.nextInvoice();
    }
    if (event.key === 'ArrowLeft' && typeof window.previousInvoice === 'function') {
      event.preventDefault();
      window.previousInvoice();
    }
  });
})();
