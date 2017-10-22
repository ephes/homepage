const coreapi = window.coreapi;
const schema = window.schema;

let auth = new coreapi.auth.SessionAuthentication({
    csrfCookieName: 'csrftoken',
    csrfHeaderName: 'X-CSRFToken'
})
let client = new coreapi.Client({auth: auth});
console.log(client);

// get/show existing images/galleries

function markableImageHandler() {
    el = $(this);
    console.log("clicked image: " + el.attr("id"));
    if (el.hasClass("border")) {
        el.removeClass("border border-primary");
    } else {
        el.addClass("border border-primary");
    }
}

function showExistingImages(images) {
    console.log(images.length);
    var preview = $("#preview-images");
    for (var i = 0; i < images.length; i++) {
        image = images[i];
        var img = $("<img></img>")
            .addClass("gallery-thumbnail")
            .addClass("gallery-image-markable")
            .attr({src: image.thumbnail_src, id: image.id})

        var thumb_div = $("<div></div>")
            .addClass("gallery-preview")
            .append(img)
        preview.append(thumb_div);
    }
    $(".gallery-image-markable" ).click(markableImageHandler);
}

let images_action = ["api", "images", "list"]
client.action(schema, images_action).then(function(result) {
    console.log(result)
    showExistingImages(result.results);
});

var galleries = {};
let galleries_action = ["api", "gallery", "list"]
client.action(schema, galleries_action).then(function(result) {
    var results = result.results;
    console.log('galleries', result);
    for (var i = 0; i < results.length; i++) {
        images = results[i]['images'].sort().join();
        console.log(images);
        galleryId = results[i]['id'];
        galleries[images] = galleryId;
    }
});

// get/show existing videos

function markableVideoHandler() {
    el = $(this);
    console.log("clicked video: " + el.attr("id"));
    if (el.hasClass("border")) {
        el.removeClass("border border-primary");
    } else {
        $(".gallery-video-markable.border" ).each(function() {
            $(this).removeClass("border border-primary");
        });
        el.addClass("border border-primary");
    }
}

function showExistingVideos(videos) {
    console.log(videos.length);
    var preview = $("#preview-videos");
    for (var i = 0; i < videos.length; i++) {
        video = videos[i];
        var video = $("<video></video>")
            .addClass("gallery-thumbnail")
            .addClass("gallery-video-markable")
            .attr({src: video.original, id: video.id})

        var thumb_div = $("<div></div>")
            .addClass("gallery-preview")
            .append(video)
        preview.append(thumb_div);
    }
    $(".gallery-video-markable" ).click(markableVideoHandler);
}

let videos_action = ["api", "videos", "list"]
client.action(schema, videos_action).then(function(result) {
    console.log(result)
    showExistingVideos(result.results);
});

var csrfToken = $('input[name=csrfmiddlewaretoken]').attr('value');
console.log(csrfToken);

function replaceWithUploadedImage(imagePk, img) {
    let action = ["api", "images", "read"];
    let params = {id: imagePk};
    console.log('params', params);
    client.action(schema, action, params).then(function(result) {
        console.log('get detail for image ' + imagePk, result);
        $(img).attr({id: imagePk, src: result.thumbnail_src})
            .removeClass('image-obj')
            .addClass('gallery-image-markable');
        $(img).click(markableImageHandler);
    });

}

function replaceWithUploadedVideo(videoPk, video) {
    let action = ["api", "videos", "read"];
    let params = {id: videoPk};
    console.log('params', params);
    client.action(schema, action, params).then(function(result) {
        console.log('get detail for video ' + videoPk, result);
        $(video).attr({id: videoPk, src: result.original})
            .removeClass('video-obj')
            .addClass('gallery-video-markable');
        $(video).click(markableVideoHandler);
    });

}

function fileUpload(thumb, file, progressBar) {
    var xhr = new XMLHttpRequest();
    console.log("file upload:", thumb, file);
    xhr.upload.addEventListener("progress", function(e) {
        if (e.lengthComputable) {
            var percentage = Math.round((e.loaded * 100) / e.total);
            console.log('progress: ' + percentage);
            progress_bar.attr({
                "aria-valuenow": percentage,
                "style": "width: " + percentage + "%",
            });
        }
    }, false);

    var uploadUrl = "/blogs/upload_image/";
    let tagName = $(thumb).prop("tagName");
    console.log("tagname: ", tagName);
    if (tagName == "VIDEO") {
        uploadUrl = "/blogs/upload_video/";
    }

    xhr.open("POST", uploadUrl);
    xhr.setRequestHeader('X-CSRFToken', csrfToken);
    var formData = new FormData();
    formData.append('original', file);
    xhr.enctype = 'mutlipart/form-data';

    xhr.onreadystatechange = function() {
        if(xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            console.log('request finished:');
            var mediaPk = xhr.responseText;
            console.log('media id: ', mediaPk);
            progress_bar.attr({
                "aria-valuenow": "100",
                "style": "width: 100%",
            });
            progressBar.remove();
            if (tagName == "VIDEO") {
                replaceWithUploadedVideo(mediaPk, thumb)
            } else {
                replaceWithUploadedImage(mediaPk, thumb)
            }
        }
    }

    xhr.send(formData);
}

function sendFiles(upload_files, upload_progress, className) {
    console.log('sendFiles..', className);
    var files = document.querySelectorAll("." + className);
    for (var i = 0; i < files.length; i++) {
        file = upload_files[i];
        progress_bar = upload_progress[i];
        fileUpload(files[i], file, progress_bar);
    }
}

function getThumbnail(tagName, className) {
    var thumb = $("<" + tagName + " />")
        .addClass("gallery-thumbnail " + className)

    var progressBar = $("<div></div>")
        .addClass("progress-bar")
        .attr({role: "progressbar", "aria-valuenow": "0", "aria-valuenow": "0",
               "aria-valuemin": "0", "aria-valuemax": "100"})

    var progressDiv = $("<div></div>")
        .addClass("progress gallery-progress-bar")
        .append(progressBar)

    var thumbDiv = $("<div></div>")
        .addClass("gallery-preview")
        .append(thumb)
        .append(progressDiv)
    return [thumb, thumbDiv, progressBar]
}

function handleImageFiles() {
    console.log('handleImageFiles');
    var files = $(this.files);
    console.log(files);
    var preview = $("#preview-images");
    var upload_files = [];
    var upload_progress = [];
    for (var i = 0, numFiles = files.length; i < numFiles; i++) {
        var file = files[i];
        console.log(file.name);
        console.log(file.size);
        console.log(file.type);
        var imageType = /^image\//;

        if (!imageType.test(file.type)) {
          continue;
        }
        var [thumb, thumbDiv, progressBar] = getThumbnail('img', 'image-obj');

        upload_files.push(file);
        upload_progress.push(progressBar);
        preview.prepend(thumbDiv);

        var reader = new FileReader();
        reader.onload = (function(aFile) { return function(e) { aFile.attr({src: e.target.result}); }; })(thumb);
        reader.readAsDataURL(file);
    }
    sendFiles(upload_files, upload_progress, 'image-obj');
}

$('#image-input').on("change", handleImageFiles);

function handleVideoFiles() {
    console.log('handleVideoFiles');
    var files = $(this.files);
    console.log(files);
    var preview = $("#preview-videos");
    var upload_files = [];
    var upload_progress = [];
    for (var i = 0, numFiles = files.length; i < numFiles; i++) {
        var file = files[i];
        console.log(file.name);
        console.log(file.size);
        console.log(file.type);
        var videoType = /^video\//;

        if (!videoType.test(file.type)) {
          continue;
        }
        var [thumb, thumbDiv, progressBar] = getThumbnail('video', 'video-obj');

        upload_files.push(file);
        upload_progress.push(progressBar);
        preview.prepend(thumbDiv);

        var reader = new FileReader();
        reader.onload = (function(aImg) { return function(e) { aImg.attr({src: e.target.result}); }; })(thumb);
        reader.readAsDataURL(file);
    }
    sendFiles(upload_files, upload_progress, 'video-obj');
}

$('#video-input').on("change", handleVideoFiles);

function getCkEditorInstance() {
    for(var instanceName in CKEDITOR.instances)
        var ckForm = CKEDITOR.instances[instanceName];
    return ckForm
}

function addGallery(imagePks, ckForm) {
    var images = imagePks.slice().sort().join();
    if (images in galleries) {
        var templateTag = "{" + "% " + "blog_gallery " + galleries[images] + " %" + "}";
        ckForm.insertHtml(templateTag);
    } else {
        let action = ["api", "gallery", "create"];
        let params = {"images": imagePks};
        console.log('params', params);
        client.action(schema, action, params).then(function(result) {
            console.log('created galleries ', result);
            galleryPk = result["id"]
            var templateTag = "{" + "% " + "blog_gallery " + galleryPk + " %" + "}";
            ckForm.insertHtml(templateTag);
            galleries[images] = galleryPk;
        });
    }
    console.log(galleries[images]);
}

function handleImageInsert() {
    console.log('handle image insert');
    var marked = $("img.border");
    var imagePks = [];
    for (var i = 0; i < marked.length; i++) {
        imagePks.push(parseInt($(marked[i]).attr("id")));
    }
    var ckForm = getCkEditorInstance();
    if (imagePks.length == 0) {
        console.log('no image media to add');
    } else if (imagePks.length == 1) {
        var imgPk = imagePks[0];
        var templateTag = "{" + "% " + "blog_image " + imgPk + " %" + "}";
        ckForm.insertHtml(templateTag);
    } else {
        addGallery(imagePks, ckForm);
    }
}

$('#insert-images').click(handleImageInsert);

function handleVideoInsert() {
    console.log('handle video insert');
    var marked = $("video.border");
    var videoPks = [];
    for (var i = 0; i < marked.length; i++) {
        videoPks.push(parseInt($(marked[i]).attr("id")));
    }
    var ckForm = getCkEditorInstance();
    if (videoPks.length == 0) {
        console.log('no video media to add');
    } else if (videoPks.length == 1) {
        var videoPk = videoPks[0];
        var templateTag = "{" + "% " + "blog_video " + videoPk + " %" + "}";
        ckForm.insertHtml(templateTag);
    } else {
        console.log('multiple videos not supported yet');
    }
}

$('#insert-video').click(handleVideoInsert);
