'use strict';

/**
 * @ngdoc function
 * @name frontendApp.controller:AboutCtrl
 * @description
 * # AboutCtrl
 * Controller of the frontendApp
 */
angular.module('frontendApp')
  .controller('PCACtrl', ['$scope', '$http', function ($scope, $http) {


    $scope.fudge = 0.0;

    
    var initializeScatter = function(id, type, xlim, ylim){
      
      // Get the initial data
      $http.get('http://localhost:5000/pca_demo?fudge_factor=0').then(
	function(resp){

	  var data = resp.data;

	  xlim = data[xlim];
	  ylim = data[ylim];

	  // Make the first scatter plot
	  var s1Plot = g3.plot(id)
	      .height(300)
              .xTitle('Component1')
              .yTitle('Component2')
	      .width(300)
	      .xTickFormat("")
	      .x2TickFormat("")
	      .y2TickFormat("")
	      .yTickFormat("")
	      //.margin(30,20,20,400)
	      .xDomain([-xlim*2, xlim*2])
	      .yDomain([-ylim*2, ylim*2])
	      .draw();

	  
	  
	  var d =  g3.scatter(s1Plot, resp.data[type]);
	  $scope[type] = d;
	  d.draw();
	})};

 var plotIG = function(){
      
      // Get the initial data
      $http.get('http://localhost:5000/pca_demo?fudge_factor=0').then(
	function(resp){

	  var data = resp.data;

	  // Make the first scatter plot
	  var s1Plot = g3.plot("#igComps")
	      .height(300)
              .xTitle('theta')
              .yTitle('amplitude')
	      .width(300)
	      .xTickFormat("")
	      .y2TickFormat("")
	      .yTickFormat("")
	      .xDomain([0, 30])
	      .yDomain([.5, -.2])
	      //.margin(30,20,20,400)
	      .draw();

	  
	  
	  g3.handle.line(s1Plot, data.i).draw();
	  g3.handle.line(s1Plot, data.g).draw();
	  d.draw();
	})};
    
 var initComps = function(){
      
      // Get the initial data
      $http.get('http://localhost:5000/pca_demo?fudge_factor=0').then(
	function(resp){

	  var data = resp.data;

	  // Make the first scatter plot
	  var s1Plot = g3.plot("#pcComps")
	      .height(300)
              .xTitle('theta')
              .yTitle('amplitude')
	      .xTickFormat("")
	      .y2TickFormat("")
	      .yTickFormat("")
	      .width(300)
	      .xDomain([0, 30])
	      .yDomain([1, -1])
	      //.margin(30,20,20,400)
	      .draw();

	  
	  
	  var c1 = g3.handle.line(s1Plot, data.c1);
	  var c2 = g3.handle.line(s1Plot, data.c2);
	  c1.draw();
	  c2.draw();

	  $scope.c1 = c1;
	  $scope.c2 = c2;

	  d.draw();
	})};

var initCurves = function(){
      
      // Get the initial data
      $http.get('http://localhost:5000/pca_demo?fudge_factor=0').then(
	function(resp){

	  var data = resp.data;
	  var curves = data.curves;

	  // Make the first scatter plot
	  var s1Plot = g3.plot("#curves")
	      .height(300)
              .xTitle('theta')
              .yTitle('amplitude')
	      .xTickFormat("")
	      .y2TickFormat("")
	      .yTickFormat("")
	      .width(300)
	      .xDomain([0, 30])
	      .yDomain([-.5, .5])
	      //.margin(30,20,20,400)
	      .draw();

	  
	  
	  $scope.curves = [];
	  
	  for(var i=0; i<curves.length; i++){
	    var curve = curves[i];
	    var plot = g3.handle.line(s1Plot, curve).opacity(.3);
	    plot.draw();
	    $scope.curves.push(plot);

	  };
	})};

    initializeScatter('#igScatter', 'ig', 'ig_xlim', 'ig_ylim');
    initializeScatter('#pcScatter', 'pc', 'pc_xlim', 'pc_ylim');
    plotIG();
    initComps();
    initCurves();

  $scope.update = function(){

      
      var fudge = $scope.fudge.toString()
      var url = 'http://localhost:5000/pca_demo?fudge_factor='.concat(fudge);
      // Get the initial data
      $http.get(url).then(
	function(resp){

	  var data = resp.data;

	  // Get the initial data
	   $scope.ig.reDraw(data.ig);
	   $scope.pc.reDraw(data.pc);
	  $scope.c1.reDraw(data.c1);
	  $scope.c2.reDraw(data.c2);

	  var curves = data.curves;
	  for( var i=0; i<curves.length; i++){
	    $scope.curves[i].reDraw(curves[i]);
	  };
	}
      )};

  }]);
