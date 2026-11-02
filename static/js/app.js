document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('[data-nav]');
  var links = document.getElementById('navLinks');
  if (toggle && links) {
    toggle.addEventListener('click', function () { links.classList.toggle('is-open'); });
  }

  var sideBtn = document.querySelector('[data-side]');
  var side = document.querySelector('.side');
  var backdrop = document.querySelector('.backdrop');
  function closeSide() {
    side && side.classList.remove('is-open');
    backdrop && backdrop.classList.remove('is-open');
  }
  if (sideBtn && side) {
    sideBtn.addEventListener('click', function () {
      side.classList.toggle('is-open');
      backdrop && backdrop.classList.toggle('is-open');
    });
    backdrop && backdrop.addEventListener('click', closeSide);
  }

  var fa = '۰۱۲۳۴۵۶۷۸۹';
  function toEn(s) {
    return String(s).replace(/[۰-۹]/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d); })
      .replace(/[٠-٩]/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(d); });
  }
  function toFa(n) {
    return String(n).replace(/\d/g, function (d) { return fa[d]; });
  }
  function group(n) {
    return toFa(Math.round(n).toLocaleString('en-US'));
  }
  document.querySelectorAll('[data-money]').forEach(function (input) {
    input.addEventListener('input', function () {
      var digits = toEn(input.value).replace(/[^\d]/g, '');
      input.value = digits ? group(parseInt(digits, 10)) : '';
    });
  });

  var calc = document.querySelector('[data-calc]');
  if (calc) {
    var rate = parseFloat(calc.dataset.rate || '6') / 100;
    var amount = calc.querySelector('[data-c-amount]');
    var months = calc.querySelector('[data-c-months]');
    function readAmount() {
      var digits = toEn(amount.value).replace(/[^\d]/g, '');
      return digits ? parseInt(digits, 10) : 0;
    }
    function paint() {
      var principal = readAmount();
      var m = parseInt(months.value, 10) || 1;
      var monthly = Math.round(principal * rate);
      var total = monthly * m;
      calc.querySelector('[data-c-monthly]').textContent = group(monthly);
      calc.querySelector('[data-c-total]').textContent = group(total);
      calc.querySelector('[data-c-return]').textContent = group(total + principal);
      var end = new Date();
      end.setMonth(end.getMonth() + m);
      calc.querySelector('[data-c-maturity]').textContent = toFa(end.toLocaleDateString('fa-IR'));
    }
    amount.addEventListener('input', paint);
    months.addEventListener('change', paint);
    paint();
  }
});
