// 웹소켓 연결
var webSock = new WebSocket("ws://192.168.10.231:8888/websocket");

// 지도 초기화 - 줌 컨트롤 및 드래그 기능 비활성화
var map = L.map('map', {
  center: [45.0, 12.0],
  zoom: 2,
  minZoom: 1,
  maxZoom: 3,
  zoomControl: true,
  dragging: true,
  doubleClickZoom: true,
  scrollWheelZoom: true,
  touchZoom: true,
  boxZoom: false,
  keyboard: false,
  attributionControl: false  // 저작권 표시 컨트롤 비활성화
});


// 전 세계 경계 (줌 레벨 2에서는 제한 X)
var worldBounds = L.latLngBounds(
  L.latLng(45.0, 12.0), 
  L.latLng(45.0, 12.0)
);

// 특정 줌 이상일 때 제한할 경계 (예: 줌 3 이상에서는 특정 지역만 이동 가능)
var limitedBounds = L.latLngBounds(
  L.latLng(-70, -180), 
  L.latLng(120, 180)
);

map.setMaxBounds(worldBounds);

// 줌 변경 시 경계 업데이트
map.on('zoomend', function () {
  if (map.getZoom() >= 3) {
      map.setMaxBounds(limitedBounds);
  } else {
      map.setMaxBounds(worldBounds); // 제한 해제
  }
});

map.on('resize', function () {
  map.invalidateSize();
})


// 타일 레이어 추가
const tileUrl = '/static/mapbox_tiles/{z}/{x}/{y}.png';
L.tileLayer(tileUrl, {
  tileSize: 512,
  zoomOffset: -1
}).addTo(map);


// 목적지 위경도좌표
/* 
var dstLatLng = new L.LatLng(window._env_.HD_LAT, window._env_.HD_LNG);
*/
// 목적지 마커 추가
/*
L.circle(dstLatLng, 110000, {
  color: "red",
  fillColor: "yellow",
  fillOpacity: 0.5,
}).addTo(map);
*/
// SVG 추가
var svg = d3
  .select(map.getPanes().overlayPane)
  .append("svg")
  .attr("class", "leaflet-zoom-animated")
  .attr("width", window.innerWidth)
  .attr("height", window.innerHeight);

// SVG 위치 조정 함수
function translateSVG() {
  var viewBoxLeft = document.querySelector("svg.leaflet-zoom-animated").viewBox.animVal.x;
  var viewBoxTop = document.querySelector("svg.leaflet-zoom-animated").viewBox.animVal.y;

  svg.attr("width", window.innerWidth);
  svg.attr("height", window.innerHeight);

  svg.attr("viewBox", function () {
    return "" + viewBoxLeft + " " + viewBoxTop + " " + window.innerWidth + " " + window.innerHeight;
  });

  svg.attr("style", function () {
    return "transform: translate3d(" + viewBoxLeft + "px, " + viewBoxTop + "px, 0px);";
  });
}

// 업데이트 함수
function update() {
  translateSVG();
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

  var min = 2.5, max = 7.5;
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

// 원 효과 함수
function handleParticle(msg, srcPoint) {
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
    .duration(2000)
    .ease(Math.sqrt)
    .attr("r", 35)
    .style("stroke-opacity", 1e-6)
    .remove();
}

// 화살표 트래픽 함수 - 수정됨 (동그라미 제거)
function handleTraffic(msg, srcPoint, hqPoint, countryMarker) {
  var fromX = srcPoint["x"];
  var fromY = srcPoint["y"];
  var toX = hqPoint["x"];
  var toY = hqPoint["y"];
  var bendArray = [true, false];
  var bend = bendArray[Math.floor(Math.random() * bendArray.length)];

  var lineData = [srcPoint, calcMidpoint(fromX, fromY, toX, toY, bend), hqPoint];
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
    .attr("stroke-width", 4)
    .attr("fill", "none");

  // 선 애니메이션
  var length = lineGraph.node().getTotalLength();
  lineGraph
    .attr("stroke-dasharray", length + " " + length)
    .attr("stroke-dashoffset", length)
    .transition()
    .duration(1000)
    .ease("ease-in")
    .attr("stroke-dashoffset", 0)
    .each("end", function () {
      // 도착 후 애니메이션 (원 효과)
      var endPoint = lineGraph.node().getPointAtLength(length);
      svg
        .append("circle")
        .attr("cx", endPoint.x)
        .attr("cy", endPoint.y)
        .attr("r", 6)
        .attr("fill", msg.color)
        .transition()
        .duration(500)
        .attr("r", 15)
        .style("opacity", 0)
        .remove();
        
      // 선 제거
      d3.select(this)
        .transition()
        .duration(100)
        .style("opacity", 0)
        .remove();
      
      // 여기서 나라 이름 마커 삭제!
      if (countryMarker) {
        country_name.removeLayer(countryMarker);
      }
    });
}


// 원 레이어 추가
var circles = new L.LayerGroup();
map.addLayer(circles);

// 원 추가 함수
function addCircle(msg, srcLatLng) {
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
  // 기존 오버레이 삭제 (너무 많아지는 것 방지)
  var countryNameCount = country_name.getLayers().length;
  var countryNameArray = country_name.getLayers();
  
  // 최대 50개의 나라명만 허용
  if (countryNameCount >= 50) {
    country_name.removeLayer(countryNameArray[0]);
  }
  
  // 나라명 마커 추가
  var countryIcon = L.divIcon({
    className: 'country-label',
    html: '<div style="color: white; text-shadow: 0.1px 0.1px 2px #000; text-align: center; width: 150px; font-size: 24px;">' + msg.country + '</div>',
    iconSize: [100, 20],
    iconAnchor: [75, 30]  // 마커 포인트의 정중앙 위에 위치하도록 조정 [width의 1/2, 높이]
  });
  
  // 나라명 마커 생성 및 추가
  var marker = L.marker(srcLatLng, {
    icon: countryIcon,
    zIndexOffset: 1000  // 다른 요소들 위에 표시
  }).addTo(country_name);
  
  // 타임아웃 삭제: 선 애니메이션 종료 시 삭제할 예정
  return marker;
}


webSock.onmessage = function (e) {
  try {
    var msg = JSON.parse(e.data);
    if (msg.type === "Traffic") {
      var dstLatLng = new L.LatLng(msg.dst_lat, msg.dst_long);
      var srcLatLng = new L.LatLng(msg.src_lat, msg.src_long);
      var hqPoint = map.latLngToLayerPoint(dstLatLng);
      var srcPoint = map.latLngToLayerPoint(srcLatLng);
      addCircle(msg, srcLatLng);
      // 수정된 부분: 반환값인 marker 저장
      var countryMarker = addCountryName(msg, srcLatLng);
      handleParticle(msg, srcPoint);
      // countryMarker를 함께 넘김
      handleTraffic(msg, srcPoint, hqPoint, countryMarker);
    }
  } catch (err) {
    console.log(err);
  }
};
