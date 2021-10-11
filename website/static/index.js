
src="jquery-3.5.1.min.js"
function loading(track_id) {
              fetch("/loading", {
                method: "POST",
                body: JSON.stringify({ track_id: track_id }),
                }).then(() => {
                window.location.href  = "/loading_page";
              })};
function recommend_track(track_id){
fetch("/recommend_track", {
  method: "POST",
  body: JSON.stringify({ track_id: track_id }),
}).then((_res) => {
  window.location.href  = "/recommend_track_results";
})}
