function pad(n) {
  return String(n).padStart(2, '0');
}
function carimbo(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}
module.exports = { carimbo };
