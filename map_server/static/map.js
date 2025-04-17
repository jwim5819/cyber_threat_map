// 웹소켓 연결
var webSock = new WebSocket(`ws://${ENV.HOST}:${ENV.PORT}/websocket`);

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
  attributionControl: false,
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

// SVG 필터 정의 (선 효과용)
var defs = svg.append("defs");

// 글로우 필터 추가 (선에만 사용)
var glowFilter = defs.append("filter")
  .attr("id", "line-glow")
  .attr("x", "-50%")
  .attr("y", "-50%")
  .attr("width", "200%")
  .attr("height", "200%");

glowFilter.append("feGaussianBlur")
  .attr("stdDeviation", "5")
  .attr("result", "coloredBlur");

var glowMerge = glowFilter.append("feMerge");
glowMerge.append("feMergeNode")
  .attr("in", "coloredBlur");
glowMerge.append("feMergeNode")
  .attr("in", "SourceGraphic");

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

// 지도 이동 시 업데이트
map.on("moveend", update);

// 곡선 중간점 계산 함수 - 수정됨
function calcMidpoint(x1, y1, x2, y2, bend) {
  // 모든 입력값이 숫자인지 확인
  if (isNaN(x1) || isNaN(y1) || isNaN(x2) || isNaN(y2)) {
    console.warn("calcMidpoint received NaN values:", { x1, y1, x2, y2 });
    // 기본값 반환 - 두 점 사이의 직선 중간점
    return { x: (x1 + x2) / 2 || 0, y: (y1 + y2) / 2 || 0 };
  }

  // 입력값 순서 정렬 로직
  if (y2 < y1 && x2 < x1) {
    var tmpy = y2;
    var tmpx = x2;
    x2 = x1;
    y1 = tmpy;
    x1 = tmpx;
  } else if (y2 < y1) {
    y1 = y2 + ((y2 = y1), 0);
  } else if (x2 < x1) {
    x1 = x2 + ((x2 = x1), 0);
  }

  // 0으로 나누기 방지
  var dx = x2 - x1;
  var dy = y2 - y1;

  // 두 점이 같은 위치인 경우(기울기 계산 불가)
  if (Math.abs(dx) < 0.0001) {
    dx = 0.0001; // 작은 값으로 설정하여 계산 오류 방지
  }

  var radian = Math.atan(-(dy / dx));
  var r = Math.sqrt(Math.abs(dx)) + Math.sqrt(Math.abs(dy));
  var m1 = (x1 + x2) / 2;
  var m2 = (y1 + y2) / 2;

  var min = 0.5,
    max = 2;
  var arcIntensity = parseFloat((Math.random() * (max - min) + min).toFixed(2));

  var a, b;
  if (bend === true) {
    a = Math.floor(m1 - r * arcIntensity * Math.sin(radian));
    b = Math.floor(m2 - r * arcIntensity * Math.cos(radian));
  } else {
    a = Math.floor(m1 + r * arcIntensity * Math.sin(radian));
    b = Math.floor(m2 + r * arcIntensity * Math.cos(radian));
  }

  // 결과 숫자 유효성 확인
  if (isNaN(a) || isNaN(b)) {
    console.warn("calcMidpoint produced NaN values:", {
      a,
      b,
      inputs: { x1, y1, x2, y2 },
    });
    return { x: m1 || 0, y: m2 || 0 }; // 중간점 반환
  }

  return { x: a, y: b };
}

// 원 효과 함수
function handleParticle(msg, srcPoint) {
  if (animationPaused) return;
  var i = 0;
  var x = srcPoint["x"];
  var y = srcPoint["y"];

  // 외부 원 - 퍼지는 효과 (기존과 동일)
  svg
    .append("circle")
    .attr("cx", x)
    .attr("cy", y)
    .attr("r", 1e-6)
    .style("fill", "none")
    .style("stroke", msg.color)
    .style("stroke-opacity", 1)
    .transition()
    .duration(1000)
    .ease(Math.sqrt)
    .attr("r", 16)
    .style("stroke-opacity", 1e-6)
    .remove();
    
 
}

// handleTraffic 함수 수정 - 선에 글로우 효과만 추가
function handleTraffic(msg, srcPoint, hqPoint, countryMarker) {
  if (animationPaused) return;
  var fromX = srcPoint["x"];
  var fromY = srcPoint["y"];
  var toX = hqPoint["x"];
  var toY = hqPoint["y"];

  // 좌표 유효성 검사
  if (isNaN(fromX) || isNaN(fromY) || isNaN(toX) || isNaN(toY)) {
    console.warn("Invalid coordinates detected:", { fromX, fromY, toX, toY });
    return; // 유효하지 않은 좌표면 애니메이션 실행하지 않음
  }

  var bendArray = [true, false];
  var bend = bendArray[Math.floor(Math.random() * bendArray.length)];

  // 중간점 계산
  var midPoint = calcMidpoint(fromX, fromY, toX, toY, bend);

  // 데이터 유효성 검사
  if (isNaN(midPoint.x) || isNaN(midPoint.y)) {
    console.warn("Invalid midpoint calculated:", midPoint);
    // 직선으로 대체
    midPoint = { x: (fromX + toX) / 2, y: (fromY + toY) / 2 };
  }

  var lineData = [srcPoint, midPoint, hqPoint];

  // 모든 좌표가 유효한지 최종 확인
  for (var i = 0; i < lineData.length; i++) {
    if (isNaN(lineData[i].x) || isNaN(lineData[i].y)) {
      console.warn("Invalid point in lineData:", i, lineData[i]);
      return; // 유효하지 않은 데이터가 있으면 중단
    }
  }

  var lineFunction = d3.svg
    .line()
    .interpolate("basis")
    .x(function (d) {
      return d.x;
    })
    .y(function (d) {
      return d.y;
    });

  try {
    // 글로우 효과가 있는 선 그래프
    var lineGraph = svg
      .append("path")
      .attr("d", lineFunction(lineData))
      .attr("opacity", 0.7)
      .attr("stroke", msg.color)
      .attr("stroke-width", 1.8)
      .attr("filter", "url(#line-glow)")  // 글로우 효과 적용
      .attr("fill", "none");

    // 선 애니메이션
    var length = lineGraph.node().getTotalLength();
    lineGraph
      .attr("stroke-dasharray", length + " " + length)
      .attr("stroke-dashoffset", length)
      .transition()
      .duration(800)
      .ease("ease-in")
      .attr("stroke-dashoffset", 0)
      .each("end", function () {
        // 도착 후 애니메이션 (원 효과)
        var endPoint = lineGraph.node().getPointAtLength(length);
        /* */
        svg
          .append("circle")
          .attr("cx", endPoint.x)
          .attr("cy", endPoint.y)
          .attr("r", 6)
          .style("fill", "none")
          .style("stroke", msg.color)
          .style("stroke-opacity", 1)
          .transition()
          .duration(1000)
          .ease(Math.sqrt)
          .attr("r", 20)
          .style("stroke-opacity", 1e-6)
          .remove();

        // A->B 방향으로 선이 사라지는 애니메이션
        d3.select(this)
          .transition()
          .duration(1000)
          .attr("stroke-dashoffset", -length) // 음수값을 주면 반대 방향으로 대시 이동
          .style("opacity", 0.7)
          .remove();

        // 나라 이름 마커 삭제
        if (countryMarker) {
          country_name.removeLayer(countryMarker);
        }
      });
  } catch (error) {
    console.error("Error creating path:", error);
  }
}

// 원 레이어 추가
var circles = new L.LayerGroup();
map.addLayer(circles);

// 원 추가 함수
function addCircle(msg, srcLatLng) {
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

// 지도 이동 시 업데이트
map.on("moveend", update);

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
  bgCircle.setAttribute("r", "28");
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
        { r: "28", strokeOpacity: "0" },
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

  // 애니메이션 원 생성
  createFixedCircleEffect("svg1", "#FF1D25");
  createFixedCircleEffect("svg2", "#B81FFF");
  createFixedCircleEffect("svg3", "#FFB72D");
}

// 애니메이션 일시 중지 함수
function pauseAnimations() {
  animationPaused = true;
}

// 애니메이션 재개 함수
function resumeAnimations() {
  // 기존 애니메이션 요소 정리
  clearExistingAnimations();

  // 애니메이션 재개
  animationPaused = false;
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

// 공격국가 TOP5 테이블 업데이트 함수 
function updateCountryStats(msg) {
  // 데이터 확인
  if (!msg.data || !Array.isArray(msg.data)) {
    console.warn("Invalid country stats data format:", msg);
    return;
  }

  // 테이블 본문 요소 가져오기
  const tbody = document.getElementById("country-attack-log");
  
  // 테이블 내용 초기화
  tbody.innerHTML = "";
  
  // 상위 5개 국가만 표시 (데이터에 더 많은 경우)
  const topCountries = msg.data.slice(0, 5);
  
  // 각 국가별 데이터를 테이블에 추가
  topCountries.forEach(country => {
    // 새 행 생성
    const row = document.createElement("tr");
    
    // 국가명 셀 (국기 포함)
    const countryCell = document.createElement("td");
    if (country.iso_code) {
      // 국기 이미지 추가 (ISO 코드가 있는 경우)
      const flagImg = document.createElement("img");
      flagImg.src = `static/flags/${country.iso_code.toUpperCase()}.png`;
      flagImg.alt = country.country || "Unknown";
      flagImg.className = "country-flag";
      flagImg.onerror = function() {
        // 국기 이미지 로드 실패 시 텍스트만 표시
        this.style.display = "none";
      };
      countryCell.appendChild(flagImg);
    }
    
    // 국가명 텍스트 추가
    const countryName = document.createElement("span");
    countryName.textContent = country.country || "Unknown";
    countryCell.appendChild(countryName);
    
    // 공격 추이 셀 (화살표 아이콘)
    const trendCell = document.createElement("td");
    const trendIcon = document.createElement("span");
    
    // 공격 추이에 따라 다른 화살표 표시
    if (country.trend > 0) {
      trendIcon.className = "trend-icon trend-up";
      trendIcon.innerHTML = "&#x2191;"; // 상승 화살표
    } else if (country.trend < 0) {
      trendIcon.className = "trend-icon trend-down";
      trendIcon.innerHTML = "&#x2193;"; // 하락 화살표
    } else {
      trendIcon.className = "trend-icon trend-stable";
      trendIcon.innerHTML = "&#x2192;"; // 가로 화살표
    }
    trendCell.appendChild(trendIcon);
    
    // 건수 셀
    const countCell = document.createElement("td");
    countCell.textContent = country.count.toLocaleString();
    
    // 행에 셀 추가
    row.appendChild(countryCell);
    row.appendChild(trendCell);
    row.appendChild(countCell);
    
    // 테이블에 행 추가
    tbody.appendChild(row);
  });
}

// 공격유형 TOP3 테이블 업데이트 함수
function updateAttackStats(msg) {
  // 데이터 확인
  if (!msg.data || !Array.isArray(msg.data)) {
    console.warn("Invalid attack stats data format:", msg);
    return;
  }

  // 테이블 본문 요소 가져오기
  const tbody = document.getElementById("attack-type-log");
  
  // 테이블 내용 초기화
  tbody.innerHTML = "";
  
  // 상위 3개 공격 유형만 표시
  const topAttackTypes = msg.data.slice(0, 3);
  
  // 각 공격 유형별 데이터를 테이블에 추가
  topAttackTypes.forEach(attackType => {
    // 새 행 생성
    const row = document.createElement("tr");
    
    // 공격 유형 셀
    const typeCell = document.createElement("td");
    typeCell.textContent = attackType.attack_type || "Unknown";
    
    // 공격 추이 셀 (화살표 아이콘)
    const trendCell = document.createElement("td");
    const trendIcon = document.createElement("span");
    
    // 공격 추이에 따라 다른 화살표 표시
    if (attackType.trend > 0) {
      trendIcon.className = "trend-icon trend-up";
      trendIcon.innerHTML = "&#x2191;"; // 상승 화살표
    } else if (attackType.trend < 0) {
      trendIcon.className = "trend-icon trend-down";
      trendIcon.innerHTML = "&#x2193;"; // 하락 화살표
    } else {
      trendIcon.className = "trend-icon trend-stable";
      trendIcon.innerHTML = "&#x2192;"; // 가로 화살표
    }
    trendCell.appendChild(trendIcon);
    
    // 건수 셀
    const countCell = document.createElement("td");
    countCell.textContent = attackType.count.toLocaleString();
    
    // 행에 셀 추가
    row.appendChild(typeCell);
    row.appendChild(trendCell);
    row.appendChild(countCell);
    
    // 테이블에 행 추가
    tbody.appendChild(row);
  });
}

// 웹소켓 메시지 처리 - 새 데이터 형식으로 업데이트
webSock.onmessage = function (e) {
  try {
    var msg = JSON.parse(e.data);
    // msg의 key에 source가 없는 경우 처리
    if (!msg.source) {
      if (!animationPaused) {
        var dstLatLng = new L.LatLng(msg.dst_lat, msg.dst_long);
        var srcLatLng = new L.LatLng(msg.latitude, msg.longitude);
  
        var hqPoint = map.latLngToLayerPoint(dstLatLng);
        var srcPoint = map.latLngToLayerPoint(srcLatLng);
  
        addCircle(msg, srcLatLng);
        var countryMarker = addCountryName(msg, srcLatLng);
        handleParticle(msg, srcPoint);
        handleTraffic(msg, srcPoint, hqPoint, countryMarker);
  
        // 어택카운트 갱신
        document.querySelector(
          ".subtitle"
        ).textContent = `${msg.event_count.toLocaleString()} ATTACKS ON THIS DAY`;
      }
    }
    // source가 있고, source가 country-stats-production인 경우
    else if (msg.source === "country-stats-production") {
      updateCountryStats(msg);
    }
    // source가 있고, source가 attack-stats-production인 경우
    else if (msg.source === "attack-stats-production") {
      updateAttackStats(msg);
    }
  } catch (err) {
    console.log(err);
  }
};

// 2시간에 한번 페이지 새로고침
setInterval(function() {
  location.reload();
}, 7200000);

// 현재시각
var Target = document.getElementById("clock");
var Target_apm = document.getElementById("apm");
function clock() {
    var time = new Date();
    var hours = time.getHours();
    var minutes = time.getMinutes();
    var seconds = time.getSeconds();
    var AmPm ="AM";
    if(hours > 12){   
        var AmPm ="PM";
        hours %= 12;
    }

    Target.innerText = 
    `${hours < 10 ? `0${hours}` : hours}:${minutes < 10 ? `0${minutes}` : minutes}:${seconds < 10 ? `0${seconds}` : seconds}`;

    Target_apm.innerText = `${AmPm}`;

}
clock();
setInterval(clock, 1000); // 1초마다 실행

// DOM이 로드되면 앱 초기화
window.addEventListener("load", initializeApp);