const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const stageLabel = document.getElementById("stageLabel");
const echoLabel = document.getElementById("echoLabel");
const hpLabel = document.getElementById("hpLabel");
const objectiveText = document.getElementById("objectiveText");

const WIDTH = canvas.width;
const HEIGHT = canvas.height;
const PLAY_BOUNDS = { left: 60, right: WIDTH - 60, top: 60, bottom: HEIGHT - 60 };
const RECORD_SECONDS = 4;
const ECHO_HOLD_SECONDS = 3;
const MAX_ECHOES = 2;
const PLAYER_MAX_HP = 5;
const TARGET_FPS = 60;

const input = {
  keys: new Set(),
  justPressed: new Set(),
  mouseDown: false,
  mouseX: WIDTH * 0.5,
  mouseY: HEIGHT * 0.5
};

const levels = [
  {
    name: "Stage 1",
    objective: "先站上踏板录一段动作，按 R 放出回响，让它替你撑开屏障。",
    intro: "回响会重演最近 4 秒，并在终点额外停留 3 秒。",
    spawn: { x: 130, y: 270 },
    plates: [
      { id: "alpha", x: 170, y: 270, w: 82, h: 82, color: "#74f0ff" }
    ],
    barriers: [
      { plateId: "alpha", x: 390, y1: 84, y2: HEIGHT - 84, width: 24 }
    ],
    core: { x: 790, y: 270, radius: 22, hp: 16 },
    turrets: []
  },
  {
    name: "Stage 2",
    objective: "门后有炮塔火力。你可以让回响替你吃线、挡弹，或者与它交叉火力。",
    intro: "子弹会被关闭状态的能量墙拦截。",
    spawn: { x: 130, y: 390 },
    plates: [
      { id: "alpha", x: 170, y: 148, w: 82, h: 82, color: "#ffb347" }
    ],
    barriers: [
      { plateId: "alpha", x: 390, y1: 84, y2: HEIGHT - 84, width: 24 }
    ],
    core: { x: 800, y: 280, radius: 22, hp: 20 },
    turrets: [
      { x: 650, y: 166, radius: 19, fireRate: 1.15, bulletSpeed: 280, range: 380 },
      { x: 730, y: 395, radius: 19, fireRate: 0.95, bulletSpeed: 250, range: 360 }
    ]
  },
  {
    name: "Stage 3",
    objective: "让回响踩住左侧踏板，你自己站上中段踏板，同时顶住双线火力击破核心。",
    intro: "最终房只要机制成立，就能以小博大。",
    spawn: { x: 130, y: 270 },
    plates: [
      { id: "alpha", x: 160, y: 140, w: 82, h: 82, color: "#74f0ff" },
      { id: "beta", x: 450, y: 392, w: 82, h: 82, color: "#ffb347" }
    ],
    barriers: [
      { plateId: "alpha", x: 280, y1: 84, y2: HEIGHT - 84, width: 22 },
      { plateId: "beta", x: 620, y1: 84, y2: HEIGHT - 84, width: 24 }
    ],
    core: { x: 820, y: 270, radius: 24, hp: 28 },
    turrets: [
      { x: 430, y: 126, radius: 19, fireRate: 1.05, bulletSpeed: 290, range: 420 },
      { x: 746, y: 146, radius: 19, fireRate: 1.2, bulletSpeed: 300, range: 420 }
    ]
  }
];

const game = {
  time: 0,
  stageIndex: 0,
  stage: null,
  player: null,
  echoes: [],
  bullets: [],
  enemyBullets: [],
  particles: [],
  notification: "",
  notificationTime: 0,
  screenShake: 0,
  flash: 0,
  stageClearTimer: 0,
  win: false
};

function deepClone(data) {
  return JSON.parse(JSON.stringify(data));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function mapMouse(event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = WIDTH / rect.width;
  const scaleY = HEIGHT / rect.height;
  input.mouseX = (event.clientX - rect.left) * scaleX;
  input.mouseY = (event.clientY - rect.top) * scaleY;
}

function onKeyDown(event) {
  if (!input.keys.has(event.code)) {
    input.justPressed.add(event.code);
  }
  input.keys.add(event.code);

  if (["KeyW", "KeyA", "KeyS", "KeyD", "Space", "KeyR", "Enter"].includes(event.code)) {
    event.preventDefault();
  }
}

function onKeyUp(event) {
  input.keys.delete(event.code);
}

window.addEventListener("keydown", onKeyDown);
window.addEventListener("keyup", onKeyUp);
canvas.addEventListener("mousemove", mapMouse);
canvas.addEventListener("mousedown", (event) => {
  mapMouse(event);
  input.mouseDown = true;
});
window.addEventListener("mouseup", () => {
  input.mouseDown = false;
});
canvas.addEventListener("mouseleave", () => {
  input.mouseDown = false;
});

function spawnParticles(x, y, color, amount, speed = 1) {
  for (let i = 0; i < amount; i += 1) {
    const angle = Math.random() * Math.PI * 2;
    const velocity = (0.6 + Math.random() * 1.4) * speed;
    game.particles.push({
      x,
      y,
      vx: Math.cos(angle) * velocity * 90,
      vy: Math.sin(angle) * velocity * 90,
      size: 1.8 + Math.random() * 3,
      life: 0.3 + Math.random() * 0.45,
      maxLife: 0.75,
      color
    });
  }
}

function shake(amount) {
  game.screenShake = Math.max(game.screenShake, amount);
}

function setNotification(text, seconds) {
  game.notification = text;
  game.notificationTime = seconds;
}

function loadStage(index, keepWin = false) {
  const definition = deepClone(levels[index]);
  definition.maxCoreHp = definition.core.hp;
  definition.plates.forEach((plate) => {
    plate.active = false;
  });
  definition.turrets.forEach((turret) => {
    turret.cooldown = 0.6;
    turret.angle = Math.PI;
  });

  game.stageIndex = index;
  game.stage = definition;
  game.echoes = [];
  game.bullets = [];
  game.enemyBullets = [];
  game.particles = [];
  game.stageClearTimer = 0;
  game.win = keepWin;
  game.player = {
    x: definition.spawn.x,
    y: definition.spawn.y,
    radius: 12,
    speed: 235,
    shotCooldown: 0,
    echoCooldown: 0,
    hp: PLAYER_MAX_HP,
    angle: 0,
    recording: []
  };
  setNotification(definition.intro, 4.5);
  updateHud();
}

function restartStage() {
  game.flash = 0;
  loadStage(game.stageIndex, false);
}

function addFriendlyBullet(source, color) {
  game.bullets.push({
    x: source.x + Math.cos(source.angle) * 18,
    y: source.y + Math.sin(source.angle) * 18,
    vx: Math.cos(source.angle) * 520,
    vy: Math.sin(source.angle) * 520,
    radius: 4,
    life: 1.15,
    color,
    damage: 1
  });
}

function addEnemyBullet(source, angle, speed) {
  game.enemyBullets.push({
    x: source.x + Math.cos(angle) * 20,
    y: source.y + Math.sin(angle) * 20,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    radius: 5,
    life: 1.8,
    color: "#ff6a6a"
  });
}

function deployEcho() {
  if (game.player.echoCooldown > 0 || game.player.recording.length < TARGET_FPS * 0.75) {
    return;
  }

  const frames = game.player.recording.map((frame) => ({ ...frame }));
  const duration = frames.length / TARGET_FPS;
  const lastFrame = frames[frames.length - 1];
  const echo = {
    x: frames[0].x,
    y: frames[0].y,
    radius: 10,
    frames,
    duration,
    age: 0,
    holdTime: ECHO_HOLD_SECONDS,
    angle: lastFrame.angle,
    shotCooldown: 0,
    hp: 2,
    expired: false
  };

  if (game.echoes.length >= MAX_ECHOES) {
    game.echoes.shift();
  }
  game.echoes.push(echo);
  game.player.echoCooldown = 0.8;
  shake(10);
  spawnParticles(game.player.x, game.player.y, "#74f0ff", 18, 1.8);
  setNotification("回响已部署。现在利用它创造第二个时间点。", 2.3);
  updateHud();
}

function barrierClosed(barrier) {
  const plate = game.stage.plates.find((item) => item.id === barrier.plateId);
  return !plate || !plate.active;
}

function resolveActor(actor, previousX) {
  actor.x = clamp(actor.x, PLAY_BOUNDS.left + actor.radius, PLAY_BOUNDS.right - actor.radius);
  actor.y = clamp(actor.y, PLAY_BOUNDS.top + actor.radius, PLAY_BOUNDS.bottom - actor.radius);

  game.stage.barriers.forEach((barrier) => {
    if (!barrierClosed(barrier)) {
      return;
    }
    if (actor.y + actor.radius < barrier.y1 || actor.y - actor.radius > barrier.y2) {
      return;
    }
    const half = barrier.width * 0.5;
    const left = barrier.x - half;
    const right = barrier.x + half;
    if (actor.x + actor.radius > left && actor.x - actor.radius < right) {
      if (previousX <= left - actor.radius) {
        actor.x = left - actor.radius;
      } else if (previousX >= right + actor.radius) {
        actor.x = right + actor.radius;
      } else {
        actor.x = actor.x < barrier.x ? left - actor.radius : right + actor.radius;
      }
    }
  });
}

function overlapsPlate(actor, plate) {
  return (
    Math.abs(actor.x - plate.x) < plate.w * 0.5 + actor.radius &&
    Math.abs(actor.y - plate.y) < plate.h * 0.5 + actor.radius
  );
}

function updatePlates() {
  const actors = [game.player, ...game.echoes.filter((echo) => !echo.expired)];
  game.stage.plates.forEach((plate) => {
    plate.active = actors.some((actor) => overlapsPlate(actor, plate));
  });
}

function damagePlayer() {
  game.player.hp -= 1;
  game.flash = 0.38;
  shake(14);
  spawnParticles(game.player.x, game.player.y, "#ff6a6a", 16, 1.9);
  if (game.player.hp <= 0) {
    setNotification("链路崩溃。按 Enter 重新开始本关。", 4);
  } else {
    setNotification("命中。继续利用回响抢时间。", 1.2);
  }
  updateHud();
}

function damageEcho(echo) {
  echo.hp -= 1;
  spawnParticles(echo.x, echo.y, "#74f0ff", 12, 1.4);
  if (echo.hp <= 0) {
    echo.expired = true;
    shake(5);
  }
  updateHud();
}

function clearStage() {
  if (game.stageClearTimer > 0) {
    return;
  }
  game.stageClearTimer = 1.5;
  shake(22);
  spawnParticles(game.stage.core.x, game.stage.core.y, "#ffb347", 40, 2.4);
  setNotification("核心崩解。时间锁松动中...", 1.5);
}

function updatePlayer(dt) {
  if (game.player.hp <= 0 || game.stageClearTimer > 0 || game.win) {
    game.player.shotCooldown = 0;
    return;
  }

  let moveX = 0;
  let moveY = 0;
  if (input.keys.has("KeyA")) moveX -= 1;
  if (input.keys.has("KeyD")) moveX += 1;
  if (input.keys.has("KeyW")) moveY -= 1;
  if (input.keys.has("KeyS")) moveY += 1;

  const length = Math.hypot(moveX, moveY) || 1;
  moveX /= length;
  moveY /= length;

  const previousX = game.player.x;
  game.player.x += moveX * game.player.speed * dt;
  game.player.y += moveY * game.player.speed * dt;
  resolveActor(game.player, previousX);

  game.player.angle = Math.atan2(input.mouseY - game.player.y, input.mouseX - game.player.x);
  game.player.shotCooldown = Math.max(0, game.player.shotCooldown - dt);
  game.player.echoCooldown = Math.max(0, game.player.echoCooldown - dt);

  const wantsFire = input.mouseDown || input.keys.has("Space");
  if (wantsFire && game.player.shotCooldown <= 0) {
    game.player.shotCooldown = 0.12;
    addFriendlyBullet(game.player, "#74f0ff");
    spawnParticles(
      game.player.x + Math.cos(game.player.angle) * 15,
      game.player.y + Math.sin(game.player.angle) * 15,
      "#74f0ff",
      4,
      0.9
    );
  }

  if (input.justPressed.has("KeyR")) {
    deployEcho();
  }

  game.player.recording.push({
    x: game.player.x,
    y: game.player.y,
    angle: game.player.angle,
    fire: wantsFire
  });
  const maxFrames = RECORD_SECONDS * TARGET_FPS;
  if (game.player.recording.length > maxFrames) {
    game.player.recording.shift();
  }
}

function updateEchoes(dt) {
  game.echoes.forEach((echo) => {
    if (echo.expired) {
      return;
    }

    echo.age += dt;
    echo.shotCooldown = Math.max(0, echo.shotCooldown - dt);

    const playbackRatio = clamp(echo.age / echo.duration, 0, 1);
    const frameIndex = Math.min(echo.frames.length - 1, Math.floor(playbackRatio * (echo.frames.length - 1)));
    const frame = echo.frames[frameIndex];
    const finalFrame = echo.frames[echo.frames.length - 1];

    if (echo.age <= echo.duration) {
      echo.x = frame.x;
      echo.y = frame.y;
      echo.angle = frame.angle;
      if (frame.fire && echo.shotCooldown <= 0) {
        echo.shotCooldown = 0.17;
        addFriendlyBullet(echo, "rgba(116, 240, 255, 0.7)");
      }
    } else {
      echo.x = finalFrame.x;
      echo.y = finalFrame.y;
      echo.angle = finalFrame.angle;
      if (echo.age > echo.duration + echo.holdTime) {
        echo.expired = true;
        spawnParticles(echo.x, echo.y, "#74f0ff", 10, 1.1);
      }
    }
  });

  game.echoes = game.echoes.filter((echo) => !echo.expired);
}

function updateTurrets(dt) {
  const actors = [game.player, ...game.echoes.filter((echo) => !echo.expired)];

  game.stage.turrets.forEach((turret) => {
    turret.cooldown -= dt;

    let target = null;
    let bestDistance = Infinity;
    actors.forEach((actor) => {
      if (actor === game.player && game.player.hp <= 0) {
        return;
      }
      const dist = distance(turret, actor);
      if (dist < bestDistance && dist < turret.range) {
        bestDistance = dist;
        target = actor;
      }
    });

    if (!target) {
      return;
    }

    turret.angle = Math.atan2(target.y - turret.y, target.x - turret.x);
    if (turret.cooldown <= 0 && game.stageClearTimer <= 0) {
      turret.cooldown = turret.fireRate;
      addEnemyBullet(turret, turret.angle, turret.bulletSpeed);
      spawnParticles(
        turret.x + Math.cos(turret.angle) * 16,
        turret.y + Math.sin(turret.angle) * 16,
        "#ff6a6a",
        5,
        1.1
      );
    }
  });
}

function bulletBlocked(bullet) {
  return game.stage.barriers.some((barrier) => {
    if (!barrierClosed(barrier)) {
      return false;
    }
    const half = barrier.width * 0.5;
    return (
      bullet.x + bullet.radius > barrier.x - half &&
      bullet.x - bullet.radius < barrier.x + half &&
      bullet.y > barrier.y1 &&
      bullet.y < barrier.y2
    );
  });
}

function updateBullets(dt) {
  game.bullets.forEach((bullet) => {
    bullet.life -= dt;
    bullet.x += bullet.vx * dt;
    bullet.y += bullet.vy * dt;
    if (
      bullet.life <= 0 ||
      bullet.x < 0 ||
      bullet.x > WIDTH ||
      bullet.y < 0 ||
      bullet.y > HEIGHT
    ) {
      bullet.dead = true;
      return;
    }
    if (bulletBlocked(bullet)) {
      bullet.dead = true;
      spawnParticles(bullet.x, bullet.y, "#ffb347", 6, 0.8);
      return;
    }
    if (distance(bullet, game.stage.core) < bullet.radius + game.stage.core.radius) {
      bullet.dead = true;
      game.stage.core.hp -= bullet.damage;
      game.flash = 0.08;
      shake(3);
      spawnParticles(bullet.x, bullet.y, "#ffb347", 8, 0.9);
      if (game.stage.core.hp <= 0) {
        clearStage();
      }
    }
  });

  game.enemyBullets.forEach((bullet) => {
    bullet.life -= dt;
    bullet.x += bullet.vx * dt;
    bullet.y += bullet.vy * dt;
    if (
      bullet.life <= 0 ||
      bullet.x < 0 ||
      bullet.x > WIDTH ||
      bullet.y < 0 ||
      bullet.y > HEIGHT
    ) {
      bullet.dead = true;
      return;
    }
    if (bulletBlocked(bullet)) {
      bullet.dead = true;
      spawnParticles(bullet.x, bullet.y, "#ff6a6a", 7, 1.1);
      return;
    }
    if (game.player.hp > 0 && distance(bullet, game.player) < bullet.radius + game.player.radius) {
      bullet.dead = true;
      damagePlayer();
      return;
    }
    const hitEcho = game.echoes.find((echo) => !echo.expired && distance(bullet, echo) < bullet.radius + echo.radius);
    if (hitEcho) {
      bullet.dead = true;
      damageEcho(hitEcho);
    }
  });

  game.bullets = game.bullets.filter((bullet) => !bullet.dead);
  game.enemyBullets = game.enemyBullets.filter((bullet) => !bullet.dead);
}

function updateParticles(dt) {
  game.particles.forEach((particle) => {
    particle.life -= dt;
    particle.x += particle.vx * dt;
    particle.y += particle.vy * dt;
    particle.vx *= 0.96;
    particle.vy *= 0.96;
  });
  game.particles = game.particles.filter((particle) => particle.life > 0);
}

function roundedRectPath(x, y, width, height, radius) {
  const clampedRadius = Math.min(radius, width * 0.5, height * 0.5);
  ctx.beginPath();
  ctx.moveTo(x + clampedRadius, y);
  ctx.lineTo(x + width - clampedRadius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + clampedRadius);
  ctx.lineTo(x + width, y + height - clampedRadius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - clampedRadius, y + height);
  ctx.lineTo(x + clampedRadius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - clampedRadius);
  ctx.lineTo(x, y + clampedRadius);
  ctx.quadraticCurveTo(x, y, x + clampedRadius, y);
  ctx.closePath();
}

function updateHud() {
  stageLabel.textContent = `${game.stageIndex + 1} / ${levels.length}`;
  echoLabel.textContent = `${game.echoes.length} / ${MAX_ECHOES}`;
  hpLabel.textContent = `${Math.max(game.player ? game.player.hp : PLAYER_MAX_HP, 0)}`;
  if (game.stage) {
    objectiveText.textContent = game.stage.objective;
  }
}

function tick(dt) {
  game.time += dt;
  game.screenShake = Math.max(0, game.screenShake - dt * 28);
  game.flash = Math.max(0, game.flash - dt * 1.8);
  game.notificationTime = Math.max(0, game.notificationTime - dt);

  if (input.justPressed.has("Enter")) {
    if (game.win) {
      loadStage(0, false);
    } else {
      restartStage();
    }
  }

  if (!game.win) {
    if (game.player.hp > 0) {
      updatePlayer(dt);
      updateEchoes(dt);
      updatePlates();
      updateTurrets(dt);
      updateBullets(dt);
    }
    updateParticles(dt);
  }

  if (game.stageClearTimer > 0) {
    game.stageClearTimer -= dt;
    if (game.stageClearTimer <= 0) {
      if (game.stageIndex >= levels.length - 1) {
        game.win = true;
        setNotification("时间锁已解除。按 Enter 再跑一轮。", 999);
      } else {
        loadStage(game.stageIndex + 1, false);
      }
    }
  }

  updateHud();
  input.justPressed.clear();
}

function drawBackdrop() {
  ctx.clearRect(0, 0, WIDTH, HEIGHT);
  ctx.fillStyle = "#050910";
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  const gradient = ctx.createRadialGradient(WIDTH * 0.5, HEIGHT * 0.5, 80, WIDTH * 0.5, HEIGHT * 0.5, 420);
  gradient.addColorStop(0, "rgba(24, 65, 89, 0.24)");
  gradient.addColorStop(1, "rgba(3, 7, 10, 0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  ctx.save();
  ctx.strokeStyle = "rgba(120, 214, 255, 0.08)";
  ctx.lineWidth = 1;
  for (let x = PLAY_BOUNDS.left; x <= PLAY_BOUNDS.right; x += 40) {
    const drift = Math.sin(game.time + x * 0.01) * 3;
    ctx.beginPath();
    ctx.moveTo(x + drift, PLAY_BOUNDS.top);
    ctx.lineTo(x + drift, PLAY_BOUNDS.bottom);
    ctx.stroke();
  }
  for (let y = PLAY_BOUNDS.top; y <= PLAY_BOUNDS.bottom; y += 40) {
    ctx.beginPath();
    ctx.moveTo(PLAY_BOUNDS.left, y);
    ctx.lineTo(PLAY_BOUNDS.right, y);
    ctx.stroke();
  }
  ctx.restore();

  ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
  ctx.lineWidth = 2;
  ctx.strokeRect(
    PLAY_BOUNDS.left,
    PLAY_BOUNDS.top,
    PLAY_BOUNDS.right - PLAY_BOUNDS.left,
    PLAY_BOUNDS.bottom - PLAY_BOUNDS.top
  );
}

function drawPlates() {
  game.stage.plates.forEach((plate) => {
    ctx.save();
    const activeAlpha = plate.active ? 0.85 : 0.24;
    ctx.fillStyle = plate.active ? `${plate.color}33` : "rgba(255,255,255,0.05)";
    ctx.strokeStyle = plate.color;
    ctx.lineWidth = plate.active ? 4 : 2;
    ctx.shadowBlur = plate.active ? 26 : 0;
    ctx.shadowColor = plate.color;
    roundedRectPath(plate.x - plate.w * 0.5, plate.y - plate.h * 0.5, plate.w, plate.h, 14);
    ctx.fill();
    ctx.globalAlpha = activeAlpha;
    ctx.stroke();
    ctx.restore();
  });
}

function drawBarriers() {
  game.stage.barriers.forEach((barrier) => {
    const open = !barrierClosed(barrier);
    const pulse = 0.55 + Math.sin(game.time * 6 + barrier.x * 0.02) * 0.2;
    ctx.save();
    ctx.lineWidth = barrier.width;
    ctx.lineCap = "round";
    ctx.strokeStyle = open ? "rgba(116, 240, 255, 0.14)" : `rgba(116, 240, 255, ${0.35 + pulse * 0.2})`;
    ctx.shadowBlur = open ? 0 : 18;
    ctx.shadowColor = "#74f0ff";
    ctx.beginPath();
    ctx.moveTo(barrier.x, barrier.y1);
    ctx.lineTo(barrier.x, barrier.y2);
    ctx.stroke();

    if (!open) {
      for (let y = barrier.y1; y <= barrier.y2; y += 20) {
        ctx.strokeStyle = `rgba(255,255,255,${0.08 + pulse * 0.08})`;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(barrier.x - barrier.width * 0.65, y);
        ctx.lineTo(barrier.x + barrier.width * 0.65, y + 10);
        ctx.stroke();
      }
    }
    ctx.restore();
  });
}

function drawCore() {
  const core = game.stage.core;
  const hpRatio = clamp(core.hp / game.stage.maxCoreHp, 0, 1);
  ctx.save();
  ctx.fillStyle = "rgba(255, 179, 71, 0.15)";
  ctx.beginPath();
  ctx.arc(core.x, core.y, core.radius + 16 + Math.sin(game.time * 5) * 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ffb347";
  ctx.shadowBlur = 28;
  ctx.shadowColor = "#ffb347";
  ctx.beginPath();
  ctx.arc(core.x, core.y, core.radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.2)";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(core.x, core.y, core.radius + 10, -Math.PI * 0.5, -Math.PI * 0.5 + Math.PI * 2 * hpRatio);
  ctx.stroke();
  ctx.restore();
}

function drawTurrets() {
  game.stage.turrets.forEach((turret) => {
    ctx.save();
    ctx.fillStyle = "#1c2d3b";
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(turret.x, turret.y, turret.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = "#ff6a6a";
    ctx.shadowBlur = 16;
    ctx.shadowColor = "#ff6a6a";
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(turret.x, turret.y);
    ctx.lineTo(
      turret.x + Math.cos(turret.angle) * (turret.radius + 10),
      turret.y + Math.sin(turret.angle) * (turret.radius + 10)
    );
    ctx.stroke();
    ctx.restore();
  });
}

function drawBullets(list) {
  list.forEach((bullet) => {
    ctx.save();
    ctx.fillStyle = bullet.color;
    ctx.shadowBlur = 12;
    ctx.shadowColor = bullet.color;
    ctx.beginPath();
    ctx.arc(bullet.x, bullet.y, bullet.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  });
}

function drawActors() {
  game.echoes.forEach((echo) => {
    const alpha = echo.age < echo.duration ? 0.8 : 0.45;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = "#74f0ff";
    ctx.shadowBlur = 18;
    ctx.shadowColor = "#74f0ff";
    ctx.beginPath();
    ctx.arc(echo.x, echo.y, echo.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(255,255,255,0.7)";
    ctx.beginPath();
    ctx.moveTo(echo.x, echo.y);
    ctx.lineTo(echo.x + Math.cos(echo.angle) * 18, echo.y + Math.sin(echo.angle) * 18);
    ctx.stroke();
    ctx.restore();
  });

  if (game.player.hp > 0) {
    ctx.save();
    ctx.fillStyle = "#74f0ff";
    ctx.shadowBlur = 22;
    ctx.shadowColor = "#74f0ff";
    ctx.beginPath();
    ctx.arc(game.player.x, game.player.y, game.player.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#ffffff";
    ctx.beginPath();
    ctx.moveTo(game.player.x, game.player.y);
    ctx.lineTo(
      game.player.x + Math.cos(game.player.angle) * 22,
      game.player.y + Math.sin(game.player.angle) * 22
    );
    ctx.stroke();
    ctx.restore();
  }
}

function drawParticles() {
  game.particles.forEach((particle) => {
    ctx.save();
    ctx.globalAlpha = clamp(particle.life / particle.maxLife, 0, 1);
    ctx.fillStyle = particle.color;
    ctx.beginPath();
    ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  });
}

function drawOverlay() {
  const chargeRatio = clamp(game.player.recording.length / (RECORD_SECONDS * TARGET_FPS), 0, 1);
  const echoCooldownRatio = clamp(game.player.echoCooldown / 0.8, 0, 1);

  ctx.save();
  ctx.fillStyle = "rgba(7, 14, 20, 0.72)";
  ctx.fillRect(24, 20, 280, 84);
  ctx.strokeStyle = "rgba(255,255,255,0.12)";
  ctx.strokeRect(24, 20, 280, 84);

  ctx.fillStyle = "#eef7ff";
  ctx.font = "700 18px Segoe UI";
  ctx.fillText(levels[game.stageIndex].name, 40, 46);

  ctx.fillStyle = "rgba(255,255,255,0.68)";
  ctx.font = "13px Segoe UI";
  ctx.fillText("Recent timeline", 40, 68);
  ctx.fillStyle = "#132430";
  ctx.fillRect(40, 76, 170, 10);
  ctx.fillStyle = "#74f0ff";
  ctx.fillRect(40, 76, 170 * chargeRatio, 10);

  ctx.fillStyle = "rgba(255,255,255,0.68)";
  ctx.fillText("Echo cooldown", 226, 68);
  ctx.fillStyle = "#132430";
  ctx.fillRect(226, 76, 56, 10);
  ctx.fillStyle = "#ffb347";
  ctx.fillRect(226, 76, 56 * (1 - echoCooldownRatio), 10);
  ctx.restore();

  if (game.notificationTime > 0 && game.notification) {
    ctx.save();
    ctx.fillStyle = "rgba(7, 14, 20, 0.82)";
    ctx.fillRect(250, HEIGHT - 72, 460, 44);
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.strokeRect(250, HEIGHT - 72, 460, 44);
    ctx.fillStyle = "#eef7ff";
    ctx.font = "14px Segoe UI";
    ctx.textAlign = "center";
    ctx.fillText(game.notification, WIDTH * 0.5, HEIGHT - 45);
    ctx.restore();
  }

  if (game.player.hp <= 0) {
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.52)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.fillStyle = "#ff6a6a";
    ctx.textAlign = "center";
    ctx.font = "700 38px Segoe UI";
    ctx.fillText("Link Lost", WIDTH * 0.5, HEIGHT * 0.5 - 12);
    ctx.fillStyle = "#eef7ff";
    ctx.font = "16px Segoe UI";
    ctx.fillText("按 Enter 重开本关", WIDTH * 0.5, HEIGHT * 0.5 + 24);
    ctx.restore();
  }

  if (game.win) {
    ctx.save();
    ctx.fillStyle = "rgba(0, 0, 0, 0.46)";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.fillStyle = "#ffb347";
    ctx.textAlign = "center";
    ctx.font = "700 40px Segoe UI";
    ctx.fillText("Time Lock Broken", WIDTH * 0.5, HEIGHT * 0.5 - 18);
    ctx.fillStyle = "#eef7ff";
    ctx.font = "16px Segoe UI";
    ctx.fillText("你完成了 30 分钟版的时间协作战斗原型。按 Enter 再来一局。", WIDTH * 0.5, HEIGHT * 0.5 + 22);
    ctx.restore();
  }
}

function render() {
  const shakeX = (Math.random() - 0.5) * game.screenShake;
  const shakeY = (Math.random() - 0.5) * game.screenShake;

  ctx.save();
  ctx.translate(shakeX, shakeY);
  drawBackdrop();
  drawPlates();
  drawBarriers();
  drawCore();
  drawTurrets();
  drawBullets(game.bullets);
  drawBullets(game.enemyBullets);
  drawActors();
  drawParticles();
  drawOverlay();

  if (game.flash > 0) {
    ctx.fillStyle = `rgba(255, 120, 120, ${game.flash * 0.2})`;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
  }
  ctx.restore();
}

let lastTime = performance.now();

function frame(now) {
  const dt = Math.min((now - lastTime) / 1000, 0.033);
  lastTime = now;
  tick(dt);
  render();
  requestAnimationFrame(frame);
}

loadStage(0, false);
requestAnimationFrame(frame);
