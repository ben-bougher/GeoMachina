'use strict';

/**
 * @ngdoc function
 * @name frontendApp.controller:AboutCtrl
 * @description
 * # AboutCtrl
 * Controller of the frontendApp
 */
angular.module('frontendApp')
  .controller('AvoCtrl', ['$scope', '$http', function ($scope, $http) {

    var convertColour = function(data, min, max){

      var cmap = d3.scale.linear().range(["white", "black"])
	  .domain([min, max]);
      var cdata = [];

      for(var i=1; i < data.length; i++){
	var row = [];
	for(var j=1; j < data[0].length; j++){
	
	  var hsl = cmap(data[i][j]);
	  row.push(hsl.toString());
	
	
	}
      cdata.push(row);
    }
    return [cdata];
    };
      
    var getOptions = function(){
      $http.get("http://localhost:5000/options").then( 
	function(resp){
	  var opts = resp.data.features;
	  $scope.selectedFeature = opts[0];
	  $scope.options.features = opts;
	});
    };

    var initializeSeismic = function(){

      // Make the seismic plot
      var vDPlot = g3.plot("#seismic")
          .height(500)
          .xTitle("spatial cross-section")
          .yTitle("")
          .width(500)
          .xTickFormat("")
	  .yTickFormat("")
          .x2TickFormat("")
          .y2TickFormat("")
          .draw();
      
      $http.get('http://localhost:5000/image_data').then(
	function(resp){
	  var data = resp.data.data;
	  $scope.vd = g3.seismic(vDPlot, convertColour(data,
						       resp.data.min,
						       resp.data.max)).draw();
	});
    };

    // Select the data using the brushes
    var Select =  function(){
      
      var extent = $scope.brush.extent();
      var x1 = extent[0][0];
      var x2 = extent[1][0];
      var y1 = extent[0][1];
      var y2 = extent[1][1];

      var selectedIndex = [];
      $scope.scatter._plot.svg().selectAll("circle").each(function(d, i){

	if((d.x > x1) && (d.x < x2) && 
	   (d.y > y1) && (d.y < y2)){
	  d.selected = true;
	  var node = d3.select(this);
	  node.attr("fill", "red");
	  selectedIndex.push(i);
	} else{
	  d.selected = false;
	  var node = d3.select(this);
	  node.attr("fill", "black");
	}
      });

      $http.post('http://localhost:5000/mask_data', {"index": selectedIndex})
	.then(function(resp){
	  $scope.vd.drawMask([resp.data.data]);
	});

    };

    var initializeScatter = function(){
      
      // Get the initial data
      $http.get('http://localhost:5000/feature_data/BasicPCA').then(
	function(resp){

	  // Make the first scatter plot
	  var s1Plot = g3.plot('#scatter')
	      .height(500)
              .xTitle('Component1')
              .yTitle('Component2')
	      .width(500)
	      .xTickFormat("")
	      .x2TickFormat("")
	      .y2TickFormat("")
	      .yTickFormat("")
	      .margin(30,20,20,400)
	      .xDomain([resp.data.xmin*1.5, resp.data.xmax*1.5])
	      .yDomain([resp.data.ymin*1.5, resp.data.ymax*1.5])
	      .draw();

	  // Add the brush
	  $scope.brush = d3.svg.brush()
	    .extent([[0, 200], [0,200]])
	    .x(s1Plot.xScale())
	    .y(s1Plot.yScale())
	    .on("brushend", Select);

	  s1Plot.svg().append("g").attr("class", "brush").call($scope.brush);


	  $scope.scatter = g3.scatter(s1Plot, resp.data.data).draw();
	
	});

    };
    
    $scope.updateScatter = function(){
      
      $http.get('http://localhost:5000/feature_data/' + 
		$scope.selectedFeature).then(
	function(resp){

	  $scope.scatter.reDraw(resp.data.data,
				[resp.data.xmin*1.5, resp.data.xmax*1.5],
				[resp.data.ymin*1.5, resp.data.ymax*1.5]);
	});
    };


    $scope.options = {};
    initializeSeismic();
    initializeScatter();
    getOptions();



  }]);










