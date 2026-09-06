let viewer;

/* Load scenes and menu */

Promise.all([
  fetch("/static/scenes.json").then(res => res.json()),
  fetch("/static/menu.json").then(res => res.json())
])

.then(([SCENES, MENU]) => {

  const DIRECTION_YAW = {
    forward: 0,
    right: 90,
    back: 180,
    left: -90
  };

  const pannellumScenes = {};

  /* ============================ */
  /* Preload panorama images      */
  /* ============================ */

  function preloadImages() {

    for (const key in SCENES) {
      const img = new Image();
      img.src = `/static/images/${SCENES[key].image}`;
    }

  }

  preloadImages();

  /* ============================ */
  /* Street style arrow hotspot   */
  /* ============================ */

  function createArrowHotspot(hotSpotDiv) {

    hotSpotDiv.classList.add("street-arrow-hotspot");

    const rotateWrapper = document.createElement("div");
    rotateWrapper.className = "arrow-rotate-wrapper";

    const arrow = document.createElement("div");
    arrow.className = "street-arrow";

    rotateWrapper.appendChild(arrow);
    hotSpotDiv.appendChild(rotateWrapper);

  }

  /* ============================ */
  /* FAST scene movement          */
  /* ============================ */

  function moveToScene(targetScene) {

    const currentZoom = viewer.getHfov();

    viewer.setHfov(currentZoom - 12, 120);

    setTimeout(() => {

      viewer.loadScene(targetScene, null, null, 200);

      setTimeout(() => {
        viewer.setHfov(currentZoom, 200);
      }, 60);

    }, 120);

  }

  /* ============================ */
  /* Build scenes                 */
  /* ============================ */

  for (const key in SCENES) {

    const scene = SCENES[key];
    console.log(scene.hotspots);

    const hotSpots = [];

    /* Navigation arrows */

    Object.keys(DIRECTION_YAW)
      .filter(dir => scene[dir])
      .forEach(dir => {

        hotSpots.push({

          pitch: -3,
          yaw: DIRECTION_YAW[dir],

          createTooltipFunc: createArrowHotspot,

          clickHandlerFunc: function () {
            moveToScene(scene[dir]);
          }

        });

      });


    /* ============================ */
    /* Admin created info hotspots  */
    /* ============================ */

    if (scene.hotspots && scene.hotspots.length > 0) {

  scene.hotspots.forEach(h => {

    hotSpots.push({
  pitch: h.pitch,
  yaw: h.yaw,
  type: "info",
  text: h.text,
  cssClass: "custom-info-hotspot"
});
  });

}

    pannellumScenes[key] = {

      type: "equirectangular",

      panorama: `/static/images/${scene.image}`,

      yaw: 180,

      hotSpots: hotSpots

    };

  }

  /* ============================ */
  /* Initialize viewer            */
  /* ============================ */

  viewer = pannellum.viewer("panorama", {

    default: {
      firstScene: Object.keys(SCENES)[0],
      autoLoad: true,
      sceneFadeDuration: 200,
      showControls: false
    },

    scenes: pannellumScenes

  });

  /* ============================ */
  /* Build top navigation menu    */
  /* ============================ */

  const menuContainer = document.getElementById("menuContainer");

  for (const block in MENU) {

    const blockItem = document.createElement("div");
    blockItem.className = "menu-block";

    const blockTitle = document.createElement("div");
    blockTitle.className = "menu-title";
    blockTitle.innerText = block;

    const dropdown = document.createElement("div");
    dropdown.className = "dropdown-menu";

    for (const floor in MENU[block]) {

      const item = document.createElement("div");
      item.className = "dropdown-item";
      item.innerText = floor;

      item.onclick = () => {
        moveToScene(MENU[block][floor]);
      };

      dropdown.appendChild(item);

    }

    blockItem.appendChild(blockTitle);
    blockItem.appendChild(dropdown);

    menuContainer.appendChild(blockItem);

  }

});


/* ============================ */
/* Information hotspot (ⓘ)      */
/* ============================ */

