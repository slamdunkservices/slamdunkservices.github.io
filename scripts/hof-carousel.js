(() => {
  const carousel = document.getElementById("hofCarousel");
  const inner = carousel?.querySelector(".carousel-inner");
  if (!carousel || !inner) return;

  const imageAlt = "Hall of Fame betting receipt";
  const eagerCount = 3;
  const interval = Number(carousel.dataset.bsInterval) || 3200;
  const manifestUrl = carousel.dataset.hofManifest || "images/hof-carousel/manifest.json";
  const imageBase = carousel.dataset.hofImageBase || "images/hof-carousel/";

  const shuffle = (items) => {
    const shuffled = [...items];
    for (let i = shuffled.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  };

  const createSlide = (filename, index) => {
    const item = document.createElement("div");
    item.className = `carousel-item${index === 0 ? " active" : ""}`;

    const image = document.createElement("img");
    image.src = `${imageBase}${filename}`;
    image.className = "d-block w-100 hof-carousel-image";
    image.alt = imageAlt;
    image.loading = index < eagerCount ? "eager" : "lazy";
    image.decoding = "async";

    item.append(image);
    return item;
  };

  const startCarousel = () => {
    const Carousel = window.bootstrap?.Carousel;
    if (!Carousel) return false;

    Carousel.getOrCreateInstance(carousel, {
      interval,
      ride: "carousel",
    }).cycle();
    return true;
  };

  const loadCarousel = async () => {
    try {
      const response = await fetch(manifestUrl);
      if (!response.ok) throw new Error(`Manifest request failed: ${response.status}`);

      const filenames = await response.json();
      if (!Array.isArray(filenames) || filenames.length === 0) {
        throw new Error("Manifest did not contain any images");
      }

      inner.replaceChildren(...shuffle(filenames).map(createSlide));
      if (!startCarousel()) {
        window.addEventListener("load", startCarousel, { once: true });
      }
    } catch (error) {
      console.error("Hall of Fame carousel failed to load.", error);
      inner.innerHTML = '<div class="hof-loading" role="status">Hall of Fame receipts could not load.</div>';
    }
  };

  loadCarousel();
})();
