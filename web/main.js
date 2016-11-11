$("form#uploader").submit(function(){
	var formData = new FormData(this);
	$.ajax({
	    url: "your_url",
	    type: "post",
	    data: formData,
	    processData: false,
	    contentType: false,
	    success: function(data) {
	    	console.log(data);
	    	if(data.prediction_result != "null" && data.error === "false") {
	    		$("#prediction_result").text("Your Image is : " + data.prediction_result)
	      		$("#may_contains").text(data.ingridients)
	    	} else if (data.error === "true") { // request is success but the data fail through validation by server
	    		$("#uploaded_image").attr("src", "no-img.jpg");
	    		$("#prediction_result").text("Your Image is : - ");
	      		$("#may_contains").text("-");
				$("#message_box").text("Unexpected Error found, " + data.error_message);
	    		$("#status_box").show();
	    	}
	    },
	    error: function(xhr, textStatus, errorThrown) {
	    	$("#message_box").text("Unexpected Error found, Please Check your Internet Connection or Image Size!");
	    	$("#status_box").show();
	    }
	});
    return false;
});


$("#photo").change(function(){
	// thanks http://stackoverflow.com/questions/4459379/preview-an-image-before-it-is-uploaded
	var reader = new FileReader();

	reader.onload = function (e) {
	// get loaded data and render thumbnail.
	$("#uploaded_image").attr("src", e.target.result);
	};

	// read the image file as a data URL.
	reader.readAsDataURL(this.files[0]);
})