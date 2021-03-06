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

      $http.get("http://ec2-52-90-110-234.compute-1.amazonaws.com/datasets").then( 
	function(resp){
	  var opts = resp.data.datasets;
	  $scope.selectedData = "reflection";
	  $scope.options.datasets = resp.data.datasets;

	  $http.get("http://ec2-52-90-110-234.compute-1.amazonaws.com/features/" + $scope.selectedData).then( 
	    function(resp){
	      var opts = resp.data.features;
	      $scope.options.features = opts;
	      $scope.selectedFeature = "IG";
	

	      initializeSeismic($scope.selectedData);
	      initializeScatter($scope.selectedData, $scope.selectedFeature);
	});
	});
    };

    var initializeSeismic = function(dataset){

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
	  .margin(30,20,20,400)
          .draw();
      
      $http.get('http://ec2-52-90-110-234.compute-1.amazonaws.com/image_data/' + dataset).then(
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

      var feature = $scope.selectedFeature;
      var dataset = $scope.selectedData;
      $http.post('http://ec2-52-90-110-234.compute-1.amazonaws.com/mask_data/' + dataset + '/' + feature, 
		 {"bounds": [x1, x2, y1, y2]})
	.then(function(resp){
	  $scope.vd.drawMask([resp.data.data]);
	});

    };

    var initializeScatter = function(dataset, feature){
      

      // Get the initial data
      $http.get('http://ec2-52-90-110-234.compute-1.amazonaws.com/feature_data/' + dataset + '/' + feature).then(
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
      
      var feature = $scope.selectedFeature;
      var dataset = $scope.selectedData;


      $http.get('http://ec2-52-90-110-234.compute-1.amazonaws.com/feature_data/' + 
		dataset + '/' + feature).then(
	function(resp){

	  $scope.scatter.reDraw(resp.data.data,
				[resp.data.xmin*1.5, resp.data.xmax*1.5],
				[resp.data.ymin*1.5, resp.data.ymax*1.5]);
	});
    };


    $scope.reset = function(){

      $('#scatter').empty();
      $('#seismic').empty();

      $http.get("http://ec2-52-90-110-234.compute-1.amazonaws.com/features/" + $scope.selectedData).then( 
	function(resp){
	  var opts = resp.data.features;
	  $scope.options.features = opts;
	  $scope.selectedFeature = opts[0];
	

	  initializeSeismic($scope.selectedData);
	  initializeScatter($scope.selectedData, $scope.selectedFeature);
    });
    };

    $scope.options = {};
    

    getOptions();

  }]);










