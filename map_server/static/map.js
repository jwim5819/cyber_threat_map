// 웹소켓 연결
var webSock = new WebSocket(`ws://${ENV.HOST}:${ENV.PORT}/websocket`);

// 어택 카운트
let attackCounter = 0;

// 공격 로그 데이터를 저장할 배열들
let countryAttackStats = {};
let attackTypeStats = {};

// 애니메이션 상태 변수 추가
let animationPaused = false;
let pendingAnimations = [];

// 지도 초기화 - 줌 컨트롤 및 드래그 기능 비활성화
var map = L.map("map", {
  center: [23.0, 12.0],
  zoom: 2,
  minZoom: 2,
  maxZoom: 2,
  zoomControl: false,
  dragging: false,
  doubleClickZoom: false,
  scrollWheelZoom: false,
  touchZoom: false,
  boxZoom: false,
  keyboard: false,
  attributionControl: false
});

// 이미지 오버레이 코드
var imageUrl = "static/images/map/worldmap_2.png";
var overlayLatLngBounds = L.latLngBounds([
  [-65, -169],
  [78, 193],
]);
var imageOverlay = L.imageOverlay(imageUrl, overlayLatLngBounds, {
  opacity: 1,
  interactive: true,
}).addTo(map);

// 전 세계 경계 (줌 레벨 2에서는 제한 X)
var worldBounds = L.latLngBounds(L.latLng(45.0, 12.0), L.latLng(45.0, 12.0));

// 특정 줌 이상일 때 제한할 경계 (예: 줌 3 이상에서는 특정 지역만 이동 가능)
var limitedBounds = L.latLngBounds(L.latLng(-70, -180), L.latLng(120, 180));

// map.setMaxBounds(worldBounds);

// 줌 변경 시 경계 업데이트
map.on("zoomend", function () {
  if (map.getZoom() >= 3) {
    map.setMaxBounds(limitedBounds);
  } else {
    map.setMaxBounds(worldBounds); // 제한 해제
  }
});

map.on("resize", function () {
  map.invalidateSize();
});

// 타일 레이어 추가
const tileUrl = "/static/images/map/mapbox_tiles/{z}/{x}/{y}.png";
L.tileLayer(tileUrl, {
  tileSize: 256,
  zoomOffset: 0,
}).addTo(map);

// SVG 추가
var svg = d3
  .select(map.getPanes().overlayPane)
  .append("svg")
  .attr("class", "leaflet-zoom-animated")
  .attr("width", window.innerWidth)
  .attr("height", window.innerHeight);

// SVG 위치 조정 함수
function translateSVG() {
  var viewBoxLeft = document.querySelector("svg.leaflet-zoom-animated").viewBox
    .animVal.x;
  var viewBoxTop = document.querySelector("svg.leaflet-zoom-animated").viewBox
    .animVal.y;

  svg.attr("width", window.innerWidth);
  svg.attr("height", window.innerHeight);

  svg.attr("viewBox", function () {
    return (
      "" +
      viewBoxLeft +
      " " +
      viewBoxTop +
      " " +
      window.innerWidth +
      " " +
      window.innerHeight
    );
  });

  svg.attr("style", function () {
    return (
      "transform: translate3d(" +
      viewBoxLeft +
      "px, " +
      viewBoxTop +
      "px, 0px);"
    );
  });
}

// 업데이트 함수
function update() {
  translateSVG();
}

function createFixedCircleEffect(svgId, color) {
  const svg = document.getElementById(svgId);

  // 기존 내용 제거
  while (svg.firstChild) {
    svg.removeChild(svg.firstChild);
  }

  // SVG 필터 정의 (블러 효과 추가)
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const filter = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "filter"
  );
  filter.setAttribute("id", "blurFilter");
  filter.setAttribute("x", "-20%");
  filter.setAttribute("y", "-20%");
  filter.setAttribute("width", "140%");
  filter.setAttribute("height", "140%");

  const feGaussianBlur = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "feGaussianBlur"
  );
  feGaussianBlur.setAttribute("stdDeviation", "2"); // 블러 강도 조절

  filter.appendChild(feGaussianBlur);
  defs.appendChild(filter);
  svg.appendChild(defs);

  // 배경 원
  const bgCircle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );
  bgCircle.setAttribute("cx", "40");
  bgCircle.setAttribute("cy", "40");
  bgCircle.setAttribute("r", "30");
  bgCircle.setAttribute("fill", color);
  bgCircle.setAttribute("fill-opacity", "0.3");
  bgCircle.setAttribute("filter", "url(#blurFilter)"); // 블러 필터 적용
  bgCircle.classList.add("bg-circle");
  svg.appendChild(bgCircle);

  // 가운데 원
  const inCircle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );
  inCircle.setAttribute("cx", "40");
  inCircle.setAttribute("cy", "40");
  inCircle.setAttribute("r", "12");
  inCircle.setAttribute("fill", color);
  inCircle.setAttribute("fill-opacity", "0.5");
  inCircle.setAttribute("filter", "url(#blurFilter)"); // 블러 필터 적용
  inCircle.classList.add("inner-circle");
  svg.appendChild(inCircle);

  // 애니메이션 원 추가
  const circle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );
  circle.setAttribute("cx", "40");
  circle.setAttribute("cy", "40");
  circle.setAttribute("r", "1");
  circle.setAttribute("stroke", color);
  circle.setAttribute("stroke-opacity", "1");
  circle.classList.add("animation-circle");

  svg.appendChild(circle);

  function animateGrowing() {
    circle.animate(
      [
        { r: "6", strokeOpacity: "1" },
        { r: "30", strokeOpacity: "0" },
      ],
      {
        duration: 1500,
        easing: "ease-out",
        iterations: Infinity,
      }
    );
  }
  animateGrowing();
}

// 지도 이동 시 업데이트
map.on("moveend", update);

// 곡선 중간점 계산 함수
function calcMidpoint(x1, y1, x2, y2, bend) {
  if (y2 < y1 && x2 < x1) {
    var tmpy = y2;
    var tmpx = x2;
    x2 = x1;
    y2 = y1;
    x1 = tmpx;
    y1 = tmpy;
  } else if (y2 < y1) {
    y1 = y2 + ((y2 = y1), 0);
  } else if (x2 < x1) {
    x1 = x2 + ((x2 = x1), 0);
  }

  var radian = Math.atan(-((y2 - y1) / (x2 - x1)));
  var r = Math.sqrt(x2 - x1) + Math.sqrt(y2 - y1);
  var m1 = (x1 + x2) / 2;
  var m2 = (y1 + y2) / 2;

  var min = 2.5,
    max = 7.5;
  var arcIntensity = parseFloat((Math.random() * (max - min) + min).toFixed(2));

  if (bend === true) {
    var a = Math.floor(m1 - r * arcIntensity * Math.sin(radian));
    var b = Math.floor(m2 - r * arcIntensity * Math.cos(radian));
  } else {
    var a = Math.floor(m1 + r * arcIntensity * Math.sin(radian));
    var b = Math.floor(m2 + r * arcIntensity * Math.cos(radian));
  }

  return { x: a, y: b };
}

// 레이어를 서서히 페이드 아웃시키는 함수 추가
function fadeOutAndRemoveLayer(layerGroup, layer, duration = 1000) {
  if (!layer) return;

  // 마커 레이어인 경우
  if (layer._icon) {
    // 마커 아이콘에 트랜지션 스타일 적용
    layer._icon.style.transition = `opacity ${duration}ms ease-out`;
    layer._icon.style.opacity = "0";

    // 마커 그림자가 있는 경우 페이드 아웃
    if (layer._shadow) {
      layer._shadow.style.transition = `opacity ${duration}ms ease-out`;
      layer._shadow.style.opacity = "0";
    }

    setTimeout(() => {
      layerGroup.removeLayer(layer);
    }, duration);
  }
  // 레이어가 있지만 다른 타입인 경우
  else {
    // DOM 요소에 접근할 수 없는 경우 바로 제거
    layerGroup.removeLayer(layer);
  }
}

// 원 효과 함수
function handleParticle(msg, srcPoint) {
  // 애니메이션 일시 중지 상태일 때는 함수 실행하지 않음
  if (animationPaused) return;

  var i = 0;
  var x = srcPoint["x"];
  var y = srcPoint["y"];

  svg
    .append("circle")
    .attr("cx", x)
    .attr("cy", y)
    .attr("r", 1e-6)
    .style("fill", "none")
    .style("stroke", msg.color)
    .style("stroke-opacity", 1)
    .transition()
    .duration(4000)
    .ease(Math.sqrt)
    .attr("r", 25)
    .style("stroke-opacity", 1e-6)
    .remove();
}

// handleTraffic 함수를 수정하여 선이 A->B 방향으로 사라지는 애니메이션 추가
function handleTraffic(msg, srcPoint, hqPoint, countryMarker) {
  // 애니메이션 일시 중지 상태일 때는 함수 실행하지 않음
  if (animationPaused) return;

  var fromX = srcPoint["x"];
  var fromY = srcPoint["y"];
  var toX = hqPoint["x"];
  var toY = hqPoint["y"];
  var bendArray = [true, false];
  var bend = bendArray[Math.floor(Math.random() * bendArray.length)];

  var lineData = [
    srcPoint,
    calcMidpoint(fromX, fromY, toX, toY, bend),
    hqPoint,
  ];
  var lineFunction = d3.svg
    .line()
    .interpolate("basis")
    .x(function (d) {
      return d.x;
    })
    .y(function (d) {
      return d.y;
    });

  var lineGraph = svg
    .append("path")
    .attr("d", lineFunction(lineData))
    .attr("opacity", 0.7)
    .attr("stroke", msg.color)
    .attr("stroke-width", 2.5)
    .attr("fill", "none");

  // 선 애니메이션
  var length = lineGraph.node().getTotalLength();
  lineGraph
    .attr("stroke-dasharray", length + " " + length)
    .attr("stroke-dashoffset", length)
    .transition()
    .duration(1800)
    .ease("ease-in")
    .attr("stroke-dashoffset", 0)
    .each("end", function () {
      // 도착 후 애니메이션 (원 효과)
      var endPoint = lineGraph.node().getPointAtLength(length);
      svg
        .append("circle")
        .attr("cx", endPoint.x)
        .attr("cy", endPoint.y)
        .attr("r", 1)
        .attr("fill", msg.color)
        .transition()
        .duration(2000)
        .attr("r", 15)
        .style("opacity", 0)
        .remove();

      // A->B 방향으로 선이 사라지는 애니메이션
      d3.select(this)
        .transition()
        .duration(1800)
        .attr("stroke-dashoffset", -length) // 음수값을 주면 반대 방향으로 대시 이동
        .style("opacity", 0.7)
        .remove();

      // 나라 이름 마커를 서서히 사라지게 함 (수정된 부분)
      if (countryMarker) {
        fadeOutAndRemoveLayer(country_name, countryMarker, 1000);
      }
    });
}

// 원 레이어 추가
var circles = new L.LayerGroup();
map.addLayer(circles);

// 원 추가 함수
function addCircle(msg, srcLatLng) {
  // 애니메이션 일시 중지 상태일 때는 함수 실행하지 않음
  if (animationPaused) return;

  circleCount = circles.getLayers().length;
  circleArray = circles.getLayers();

  // 최대 50개의 원만 허용
  if (circleCount >= 1) {
    circles.removeLayer(circleArray[0]);
  }

  L.circle(srcLatLng, 50000, {
    color: msg.color,
    fillColor: msg.color,
    fillOpacity: 0.2,
  }).addTo(circles);
}

// 나라명 오버레이
var country_name = new L.LayerGroup();
map.addLayer(country_name);

// 나라명 오버레이 함수 - 수정됨
function addCountryName(msg, srcLatLng) {
  // 애니메이션 일시 중지 상태일 때는 null 반환
  if (animationPaused) return null;

  // 기존 오버레이 삭제 (너무 많아지는 것 방지)
  var countryNameCount = country_name.getLayers().length;
  var countryNameArray = country_name.getLayers();

  // 최대 50개의 나라명만 허용
  if (countryNameCount >= 50) {
    country_name.removeLayer(countryNameArray[0]);
  }

  // 나라명 마커 추가
  var countryIcon = L.divIcon({
    className: "country-label",
    html:
      '<div style="color: white; text-shadow: 0.1px 0.1px 2px #000; text-align: center; width: 150px; font-size: 16px;">' +
      msg.country +
      "</div>",
    iconSize: [100, 20],
    iconAnchor: [75, 30], // 마커 포인트의 정중앙 위에 위치하도록 조정 [width의 1/2, 높이]
  });

  // 나라명 마커 생성 및 추가
  var marker = L.marker(srcLatLng, {
    icon: countryIcon,
    zIndexOffset: 1000, // 다른 요소들 위에 표시
  }).addTo(country_name);

  // 타임아웃 삭제: 선 애니메이션 종료 시 삭제할 예정
  return marker;
}

// 컨테이너 리사이징 함수
function resizeContainer() {
  const wrapperContainer = document.getElementById("map-container-wrapper");
  const mapContainer = document.getElementById("map-container");
  let scaled = true;

  document.body.classList.toggle("scaled", scaled);
  const wrapperContainerWidth = wrapperContainer.offsetWidth;
  const wrapperContainerHeight = wrapperContainer.offsetHeight;

  // 스케일 비율 계산
  const widthRatio = wrapperContainerWidth / 1030;
  const heightRatio = wrapperContainerHeight / 600;
  const scaleRatio = Math.min(widthRatio, heightRatio);

  // CSS 변수로 스케일 비율 설정
  document.documentElement.style.setProperty("--scale-ratio", scaleRatio);
}

// 국가별 통계 업데이트 함수
function updateCountryStats(country, countryToCodeMap) {
  if (!country || country === "Unknown") return;

  // 국가 코드 찾기
  let countryCode = "";
  if (countryToCodeMap && typeof countryToCodeMap === "object") {
    countryCode = countryToCodeMap[country] || "";
  }

  if (!countryAttackStats[country]) {
    countryAttackStats[country] = {
      count: 1,
      trend: "same", // 기본값
      code: countryCode,
    };
  } else {
    countryAttackStats[country].count++;
    countryAttackStats[country].trend = "up"; // 증가 추세로 표시
    if (countryCode && !countryAttackStats[country].code) {
      countryAttackStats[country].code = countryCode;
    }
  }

  // TOP5 테이블 업데이트
  updateCountryTable();
}

// 공격 유형별 통계 업데이트 함수
function updateAttackTypeStats(attackType) {
  if (!attackType || attackType === "Unknown") return;

  if (!attackTypeStats[attackType]) {
    attackTypeStats[attackType] = {
      count: 1,
      trend: "same", // 기본값
    };
  } else {
    attackTypeStats[attackType].count++;
    attackTypeStats[attackType].trend = "up"; // 증가 추세로 표시
  }

  // TOP5 테이블 업데이트
  updateAttackTypeTable();
}

// 국가별 TOP5 테이블 업데이트
function updateCountryTable() {
  const tableBody = document.getElementById("country-attack-log");
  tableBody.innerHTML = ""; // 테이블 초기화

  // 객체를 배열로 변환하고 건수 기준으로 정렬
  const sortedCountries = Object.keys(countryAttackStats)
    .map((country) => ({
      name: country,
      count: countryAttackStats[country].count,
      trend: countryAttackStats[country].trend,
      code: countryAttackStats[country].code,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // TOP5만 선택

  // 실제 데이터 행 채우기
  sortedCountries.forEach((country) => {
    const row = document.createElement("tr");

    // 트렌드 아이콘 결정
    let trendIcon = "■";
    let trendClass = "trend-same";

    if (country.trend === "up") {
      trendIcon = "▲";
      trendClass = "trend-up";
    } else if (country.trend === "down") {
      trendIcon = "▼";
      trendClass = "trend-down";
    }

    // 국기 이미지 태그 생성
    let flagImg = "";
    if (country.code) {
      flagImg = `<img src="/static/flags/${country.code}.png" alt="${country.name} 국기" class="country-flag">`;
    }

    // 각 열에 데이터 추가
    row.innerHTML = `
      <td data-full-text="${country.name}">${flagImg} ${country.name}</td>
      <td><span class="${trendClass}">${trendIcon}</span></td>
      <td>${country.count.toLocaleString()}</td>
    `;

    tableBody.appendChild(row);
  });

  // 남은 빈 행 채우기 (5행을 채울때까지)
  const remainingRows = 5 - sortedCountries.length;
  for (let i = 0; i < remainingRows; i++) {
    const emptyRow = document.createElement("tr");
    emptyRow.innerHTML = `
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
    `;
    tableBody.appendChild(emptyRow);
  }
}

// 공격 유형별 TOP5 테이블 업데이트
function updateAttackTypeTable() {
  const tableBody = document.getElementById("attack-type-log");
  tableBody.innerHTML = ""; // 테이블 초기화

  // 객체를 배열로 변환하고 건수 기준으로 정렬
  const sortedTypes = Object.keys(attackTypeStats)
    .map((type) => ({
      name: type,
      count: attackTypeStats[type].count,
      trend: attackTypeStats[type].trend,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // TOP5만 선택

  // 실제 데이터 채우기
  sortedTypes.forEach((type) => {
    const row = document.createElement("tr");

    // 트렌드 아이콘 결정
    let trendIcon = "■";
    let trendClass = "trend-same";

    if (type.trend === "up") {
      trendIcon = "▲";
      trendClass = "trend-up";
    } else if (type.trend === "down") {
      trendIcon = "▼";
      trendClass = "trend-down";
    }

    // 각 열에 데이터 추가
    row.innerHTML = `
      <td data-full-text="${type.name}">${type.name}</td>
      <td><span class="${trendClass}">${trendIcon}</span></td>
      <td>${type.count.toLocaleString()}</td>
    `;

    tableBody.appendChild(row);
  });

  // 남은 빈 행 채우기 (5행을 채울때까지)
  const remainingRows = 5 - sortedTypes.length;
  for (let i = 0; i < remainingRows; i++) {
    const emptyRow = document.createElement("tr");
    emptyRow.innerHTML = `
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
    `;
    tableBody.appendChild(emptyRow);
  }
}

// 페이지 가시성 변경 핸들러
function handleVisibilityChange() {
  if (document.hidden) {
    // 페이지가 숨겨진 경우 애니메이션 일시 중지
    pauseAnimations();
  } else {
    // 페이지가 다시 보이는 경우 애니메이션 재개
    resumeAnimations();
  }
}

// 애니메이션 일시 중지 함수
function pauseAnimations() {
  animationPaused = true;
  console.log("Animation paused due to page visibility change");
}

// 애니메이션 재개 함수
function resumeAnimations() {
  // 기존 애니메이션 요소 정리
  clearExistingAnimations();

  // 애니메이션 재개
  animationPaused = false;
  console.log("Animation resumed");
}

// 기존 애니메이션 요소 정리 함수
function clearExistingAnimations() {
  // SVG 애니메이션 요소 제거 (원, 선 등)
  svg.selectAll("circle").interrupt().remove();
  svg.selectAll("path").interrupt().remove();

  // 마커와 원도 제거 (필요에 따라 주석 처리 가능)
  country_name.clearLayers();
  circles.clearLayers();
}

// 초기화 및 이벤트 핸들러
function initializeApp() {
  // 초기 리사이징 적용
  resizeContainer();

  // 창크기변화 감지
  window.addEventListener("resize", resizeContainer);

  // 전체화면 감지
  window.addEventListener("fullscreenchange", resizeContainer);

  // 페이지 가시성 변경 감지 이벤트 리스너 추가
  document.addEventListener("visibilitychange", handleVisibilityChange);

  // 테이블 초기화
  updateCountryTable();
  updateAttackTypeTable();
  initializeAttackTypeTable();
  initializeCountryTable();
  // 애니메이션 원 생성
  createFixedCircleEffect("svg1", "#FF1D25");
  createFixedCircleEffect("svg2", "#B81FFF");
  createFixedCircleEffect("svg3", "#FFB72D");
}

// 국가별 TOP5 테이블 초기화 함수
function initializeCountryTable() {
  const tableBody = document.getElementById("country-attack-log");
  tableBody.innerHTML = ""; // 테이블 초기화

  // 5개의 빈 행 추가
  for (let i = 0; i < 5; i++) {
    const row = document.createElement("tr");
    // 플레이스홀더 내용 추가
    row.innerHTML = `
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
    `;
    tableBody.appendChild(row);
  }
}

// 공격 유형별 TOP5 테이블 초기화
function initializeAttackTypeTable() {
  const tableBody = document.getElementById("attack-type-log");
  tableBody.innerHTML = ""; // 테이블 초기화

  // 5개의 빈 행 추가
  for (let i = 0; i < 5; i++) {
    const row = document.createElement("tr");
    // 플레이스홀더 내용 추가
    row.innerHTML = `
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
      <td class="empty-row">&nbsp;</td>
    `;
    tableBody.appendChild(row);
  }
}

// 웹소켓 메시지 처리
webSock.onmessage = function (e) {
  try {
    var msg = JSON.parse(e.data);
    if (msg.type === "Traffic") {
      // 항상 통계는 업데이트
      attackCounter++;
      document.querySelector(
        ".subtitle"
      ).textContent = `${attackCounter.toLocaleString()} ATTACKS ON THIS DAY`;

      // 국가별 통계 업데이트
      updateCountryStats(msg.country || "Unknown", msg.country_to_code);

      // 공격 유형별 통계 업데이트
      updateAttackTypeStats(msg.protocol || "Unknown");

      // 페이지가 보이는 상태일 때만 애니메이션 표시
      if (!animationPaused) {
        var dstLatLng = new L.LatLng(msg.dst_lat, msg.dst_long);
        var srcLatLng = new L.LatLng(msg.src_lat, msg.src_long);
        var hqPoint = map.latLngToLayerPoint(dstLatLng);
        var srcPoint = map.latLngToLayerPoint(srcLatLng);
        addCircle(msg, srcLatLng);
        var countryMarker = addCountryName(msg, srcLatLng);
        handleParticle(msg, srcPoint);
        handleTraffic(msg, srcPoint, hqPoint, countryMarker);
      }
    }
  } catch (err) {
    console.log(err);
  }
};

// DOM이 로드되면 앱 초기화
window.addEventListener("load", initializeApp);
