(() => {
  const EXCLUDED_PATHS = new Set(['/about.html','/privacy.html','/contact.html']);
  if (EXCLUDED_PATHS.has(location.pathname)) return;

  const creatives = {
    banner: {
      href: 'https://px.a8.net/svt/ejp?a8mat=4BC7V4+T6AYQ+3SPO+HY7W1',
      img: 'https://www20.a8.net/svt/bgt?aid=260910544049&wid=003&eno=01&mid=s00000017718003015000&mc=1',
      width: 468,
      height: 60,
      track: 'https://www10.a8.net/0.gif?a8mat=4BC7V4+T6AYQ+3SPO+HY7W1'
    },
    squareA: {
      href: 'https://px.a8.net/svt/ejp?a8mat=4BC7V4+15OEO2+34XA+ZTV6P',
      img: 'https://www20.a8.net/svt/bgt?aid=260910544070&wid=003&eno=01&mid=s00000014635006018000&mc=1',
      width: 300,
      height: 250,
      track: 'https://www17.a8.net/0.gif?a8mat=4BC7V4+15OEO2+34XA+ZTV6P'
    },
    squareB: {
      href: 'https://px.a8.net/svt/ejp?a8mat=4BC7V3+GDF77M+1MWA+15UK41',
      img: 'https://www29.a8.net/svt/bgt?aid=260910543990&wid=003&eno=01&mid=s00000007633007029000&mc=1',
      width: 300,
      height: 250,
      track: 'https://www11.a8.net/0.gif?a8mat=4BC7V3+GDF77M+1MWA+15UK41'
    }
  };

  function injectStyle(){
    if (document.getElementById('a8-affiliate-style')) return;
    const s = document.createElement('style');
    s.id = 'a8-affiliate-style';
    s.textContent = `
      .a8-ad-slot{width:min(100%,520px);margin:28px auto;text-align:center;position:relative}
      .a8-ad-slot.square{width:min(100%,340px)}
      .a8-ad-label{font-size:9px;letter-spacing:.08em;color:#9aa5b4;margin:0 0 6px;font-weight:700}
      .a8-ad-box{display:inline-block;max-width:100%;padding:8px;border:1px solid #edf1f5;border-radius:14px;background:#fff;box-shadow:0 8px 24px rgba(49,78,104,.05)}
      .a8-ad-box a{display:block;line-height:0}
      .a8-ad-box img.a8-creative{display:block;max-width:100%;height:auto;border:0}
      .a8-ad-pixel{position:absolute!important;width:1px!important;height:1px!important;opacity:0;pointer-events:none}
      .side .a8-ad-slot{margin:0 0 18px;width:100%}
      .side .a8-ad-box{width:100%}
      @media(max-width:560px){.a8-ad-slot{margin:20px auto}.a8-ad-box{padding:6px;border-radius:11px}}
    `;
    document.head.appendChild(s);
  }

  function adElement(c, type, eventName){
    const wrap = document.createElement('div');
    wrap.className = 'a8-ad-slot' + (type === 'square' ? ' square' : ' banner');
    wrap.setAttribute('aria-label','広告');

    const label = document.createElement('div');
    label.className = 'a8-ad-label';
    label.textContent = '広告・PR';

    const box = document.createElement('div');
    box.className = 'a8-ad-box';

    const a = document.createElement('a');
    a.href = c.href;
    a.rel = 'nofollow sponsored';
    a.dataset.gaEvent = eventName;
    a.dataset.gaPlacement = type;

    const img = document.createElement('img');
    img.className = 'a8-creative';
    img.src = c.img;
    img.width = c.width;
    img.height = c.height;
    img.alt = '広告';
    img.loading = 'lazy';
    img.decoding = 'async';

    const track = document.createElement('img');
    track.className = 'a8-ad-pixel';
    track.src = c.track;
    track.width = 1;
    track.height = 1;
    track.alt = '';

    a.appendChild(img);
    box.appendChild(a);
    box.appendChild(track);
    wrap.appendChild(label);
    wrap.appendChild(box);
    return wrap;
  }

  function chooseSquare(){
    const day = new Date().getUTCDate();
    const score = [...location.pathname].reduce((n,ch)=>n+ch.charCodeAt(0),0) + day;
    return score % 2 === 0 ? creatives.squareA : creatives.squareB;
  }

  function placeBanner(){
    const ad = adElement(creatives.banner,'banner','a8_banner_click');
    const heroShell = document.querySelector('.hero-shell');
    if (heroShell){
      heroShell.insertAdjacentElement('afterend', ad);
      return;
    }
    const statusHero = document.querySelector('.status-page-hero');
    if (statusHero){
      statusHero.insertAdjacentElement('afterend', ad);
      return;
    }
    const seoHero = document.querySelector('section.hero');
    if (seoHero){
      seoHero.insertAdjacentElement('afterend', ad);
      return;
    }
    const main = document.querySelector('main');
    if (main) main.insertAdjacentElement('afterbegin', ad);
  }

  function placeSquare(){
    const ad = adElement(chooseSquare(),'square','a8_square_click');
    const side = document.querySelector('.side');
    if (side){
      side.insertAdjacentElement('afterbegin', ad);
      return;
    }
    const national = document.querySelector('.national-insights');
    if (national){
      national.insertAdjacentElement('afterend', ad);
      return;
    }
    const statusGrid = document.querySelector('.status-page-grid');
    if (statusGrid){
      statusGrid.insertAdjacentElement('afterend', ad);
      return;
    }
    const footer = document.querySelector('.site-footer,.footer');
    if (footer) footer.insertAdjacentElement('beforebegin', ad);
  }

  function init(){
    if (document.querySelector('.a8-ad-slot')) return;
    injectStyle();
    placeBanner();
    placeSquare();
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded',init,{once:true});
  } else {
    init();
  }
})();
