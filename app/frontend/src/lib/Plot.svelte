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
         marker: { size: 4 },
         name: 'Raw',
      };

      const traceTempFilt = {
         x: plotData.temp_filt.x,
         y: plotData.temp_filt.y,
         mode: 'lines',
         line: { width: 0.8 },
         name: 'TempS',
      };

      const traceTempZB = {
         x: plotData.temp_zb.x,
         y: plotData.temp_zb.y,
         mode: 'markers',
         marker: { size: 4 },
         name: 'TempZb',
      };

      const traceForecast = {
         x: plotData.forecast.x,
         y: plotData.forecast.y,
         mode: 'lines',
         line: { width: 0.8 },
         name: 'Forecast',
      };

      const layout = {
         width: 1200,
         title: `Home Temperature Sensors`,
         xaxis: {
            tickmode: 'linear',
            dtick: 6 * 60 * 60 * 1000,
            tickformat: "%H:%M",
            tickformatstops: [
               { dtickrange: [null, 86400000], value: "%d/%m" },
               { dtickrange: [86400000, null], value: "%H:%M" }
            ]
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
