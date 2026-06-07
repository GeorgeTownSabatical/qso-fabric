(function () {
  const star = document.getElementById("star");
  const metrics = document.getElementById("metrics");

  window.renderStellarState = function renderStellarState(state) {
    const mass = Number(state.mass || 1);
    const luminosity = Number(state.luminosity || 1);
    const entropy = Number(state.entropy_index || 0);
    const magnetic = Number(state.magnetic_field || 1);
    const fusion = Number(state.fusion_rate || 1);

    const size = Math.max(80, Math.min(280, 120 + mass * 14));
    const glow = Math.max(10, Math.min(90, 18 + luminosity * 12));
    const saturation = Math.max(35, Math.min(95, 90 - entropy * 28));
    const hue = Math.max(5, Math.min(210, 35 + magnetic * 75));
    const flicker = Math.max(0.35, Math.min(2.25, fusion));

    star.style.width = `${size}px`;
    star.style.height = `${size}px`;
    star.style.boxShadow = `0 0 ${glow}px hsla(${hue}, ${saturation}%, 60%, 0.85)`;
    star.style.filter = `hue-rotate(${entropy * 18}deg)`;
    star.style.animation = `solis-flicker ${1 / flicker}s infinite alternate ease-in-out`;

    metrics.textContent = `mass=${mass.toFixed(3)} lum=${luminosity.toFixed(3)} entropy=${entropy.toFixed(3)} magnetic=${magnetic.toFixed(3)} fusion=${fusion.toFixed(3)}`;
  };

  const style = document.createElement("style");
  style.textContent = `@keyframes solis-flicker { from { transform: scale(0.985); } to { transform: scale(1.015); } }`;
  document.head.appendChild(style);
})();
