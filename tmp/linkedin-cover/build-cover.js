const fs = require("fs");
const sharp = require("sharp");

const width = 3168;
const height = 792;
const sourceBackground =
  "/Users/jim/.codex/generated_images/019f7b42-16cd-78a2-8d6f-e3651b346c61/call_fD13m7HnuPKj07yzQEi6EYHt.png";
const sourceLogo = "/Users/jim/Desktop/logo-horizontal-dark.svg";
const output =
  "/Users/jim/Code/slamdunkservices.github.io/images/linkedin-cover-slam-dunk-bets-3168x792.jpg";

const logoSvg = fs
  .readFileSync(sourceLogo, "utf8")
  .replace('<rect width="520" height="200" fill="#0a0a0a"></rect>', "");

const focusOverlay = Buffer.from(`
  <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <defs>
      <radialGradient id="focus" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#050505" stop-opacity="0.94"/>
        <stop offset="58%" stop-color="#050505" stop-opacity="0.68"/>
        <stop offset="100%" stop-color="#050505" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="edge" x1="0" x2="1">
        <stop offset="0%" stop-color="#050505" stop-opacity="0.55"/>
        <stop offset="36%" stop-color="#050505" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <ellipse cx="1640" cy="396" rx="980" ry="360" fill="url(#focus)"/>
    <rect width="${width}" height="${height}" fill="url(#edge)"/>
  </svg>
`);

async function build() {
  const logo = await sharp(Buffer.from(logoSvg))
    .resize({ width: 1500 })
    .png()
    .toBuffer();

  await sharp(sourceBackground)
    .resize(width, height, { fit: "cover", position: "centre" })
    .composite([
      { input: focusOverlay, left: 0, top: 0 },
      { input: logo, left: 860, top: 108 },
    ])
    .flatten({ background: "#0a0a0a" })
    .jpeg({ quality: 94, chromaSubsampling: "4:4:4", progressive: true })
    .toFile(output);

  console.log(output);
}

build();
