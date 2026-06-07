(function () {
  // Client-side rendering is projection only. No simulation is run in browser.
  const demoStates = [
    { mass: 1.2, luminosity: 1.1, entropy_index: 0.1, magnetic_field: 0.95, fusion_rate: 0.92 },
    { mass: 1.3, luminosity: 1.4, entropy_index: 0.13, magnetic_field: 0.9, fusion_rate: 1.05 },
    { mass: 1.4, luminosity: 1.6, entropy_index: 0.18, magnetic_field: 0.84, fusion_rate: 1.2 }
  ];

  let idx = 0;
  setInterval(() => {
    if (typeof window.renderStellarState === "function") {
      window.renderStellarState(demoStates[idx % demoStates.length]);
      idx += 1;
    }
  }, 1000);
})();
