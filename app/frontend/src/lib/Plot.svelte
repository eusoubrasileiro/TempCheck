<script>
   import { onMount } from 'svelte';
   import Plotly from 'plotly.js-basic-dist';

   let plotData;

   async function fetchData() {
      const response = await fetch('/data'); // Modify this endpoint to point to your Python server
      plotData = await response.json();
      plotGraph();
   }

   function plotGraph() {
      const traceRaw = {
         x: plotData.raw.x,
         y: plotData.raw.y,
         mode: 'markers',
         marker: { size: 3, opacity: 0.3 },
         name: 'Raw',
      };

      const traceTempFilt = {
         x: plotData.temp_filt.x,
         y: plotData.temp_filt.y,
         mode: 'lines',
         line: { width: 1.8, color: 'black' },
         name: 'TempS',
      };

      const traceTempZB = {
         x: plotData.temp_zb.x,
         y: plotData.temp_zb.y,
         mode: 'markers',
         marker: { size: 3, opacity : 0.3, symbol: 'x'},
         name: 'TempZb',
      };

      const traceForecast = {
         x: plotData.forecast.x,
         y: plotData.forecast.y,
         mode: 'lines',
         line: { width: 1.5, color: 'red'},
         name: 'Forecast',
      };

      const layout = {
         width: 1200,
         title: 'Home Temperature Sensors',
         xaxis: {
            tickmode: 'linear',
            dtick: 6 * 60 * 60 * 1000,  // 6 hours in milliseconds
            tickformat: "%H:%M<br>%d/%m",  // Hour on top and date on bottom
            tickformatstops: [
                  // For 6-hour intervals or shorter, display hour and date in two lines
                  { dtickrange: [null, 6 * 60 * 60 * 1000], value: "%H:%M<br>%d/%m" },
                  // For intervals longer than 6 hours, you can adjust if needed
                  { dtickrange: [6 * 60 * 60 * 1000, null], value: "%H:%M<br>%d/%m" }
            ],
            hoverformat: "%d/%m %H:%M",  // Customize hover labels to show day, hour, minute
         },
         yaxis: {
            title: 'Temperature (°C)',
            range: [21, 33],
         },
      };

      Plotly.newPlot('plot', [traceRaw, traceTempFilt, traceTempZB, traceForecast], layout);
   }

   onMount(() => {
      fetchData();
      setInterval(fetchData, 2 * 60 * 1000);  // Auto-refresh every 2 minutes
   });
</script>

<div id="plot"></div>
