<script>
   import { onMount } from 'svelte';
   import Plotly from 'plotly.js-basic-dist';

   let plotData;

   async function fetchData() {
      const response = await fetch('/data'); // Modify this endpoint to point to your Python server
      plotData = await response.json();
      plotGraph();
   }

   function generateTicks(data) {
    const tickvals = [];
    const ticktext = [];
    
    const oneDay = 24 * 60 * 60 * 1000;  // One day in milliseconds
    const sixHours = 6 * 60 * 60 * 1000;  // Six hours in milliseconds

    const getBeginDay = (date) => {
      return new Date(new Date(date).toDateString());
    };
    
    // Get the first timestamp from data and use it get the 00:00 hours
    let startTime = getBeginDay(data.raw.x[0]).getTime();  
    let endTime = getBeginDay(data.raw.x[data.raw.x.length - 1]).getTime() + oneDay;  // Last timestamp midnight 

    // Loop through time range, adding ticks every 6 hours
    for (let time = startTime; time <= endTime; time += sixHours) {
        let date = new Date(time);
        tickvals.push(time);  // Add the current time to tickvals
        // Check if it's new day adding date at first tick hour
        if (date.getHours() === 0) {
            ticktext.push(date.getHours() + 'h<br>' + date.getDate() + '/' + (date.getMonth() + 1));  // Show the date at midnight
        } else {
            ticktext.push(date.getHours() +'h');  // Show the hour for other times
        }
    }

    return { tickvals, ticktext };
   }


   function plotGraph() {
      const yhover = '%{y:.2f}°C<br>%{x}<extra></extra>'; 

      const traceRaw = {
         x: plotData.raw.x,
         y: plotData.raw.y,
         mode: 'markers',
         marker: { size: 3, opacity: 0.3 },
         name: 'Raw',
         hovertemplate : yhover,
      };

      const traceTempFilt = {
         x: plotData.temp_filt.x,
         y: plotData.temp_filt.y,
         mode: 'lines',
         line: { width: 1.8, color: 'black' },
         name: 'TempS',
         hovertemplate : yhover,
      };

      const traceTempZB = {
         x: plotData.temp_zb.x,
         y: plotData.temp_zb.y,
         mode: 'markers',
         marker: { size: 3, opacity : 0.3, symbol: 'x'},
         name: 'TempZb',
         hovertemplate : yhover,
      };

      const traceForecast = {
         x: plotData.forecast.x,
         y: plotData.forecast.y,
         mode: 'lines',
         line: { width: 1.5, color: 'red'},
         name: 'Forecast',
         hovertemplate : yhover,
      };

      const ticks = generateTicks(plotData);  // Assuming 'data' is your dataset

      const layout = {
         width: 1200,         
         xaxis: {
            tickmode: 'array',            
            tickvals: ticks.tickvals,  // Custom tick positions
            ticktext: ticks.ticktext,  // Custom tick labels
            hoverformat: "%d/%m %H:%M",  // Customize hover labels to show day, hour, minute
         },
         yaxis: {
            title: 'Temperature (°C)',
            range: [21, 33]            
         },
         hovermode: 'closest',
      };

      Plotly.newPlot('plot', [traceRaw, traceTempFilt, traceTempZB, traceForecast], layout);
   }

   onMount(() => {
      fetchData();
      setInterval(fetchData, 2 * 60 * 1000);  // Auto-refresh every 2 minutes
   });
</script>

<div id="plot"></div>
