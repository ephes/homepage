const coreapi = window.coreapi;
const schema = window.schema;

let auth = new coreapi.auth.SessionAuthentication({
    csrfCookieName: 'csrftoken',
    csrfHeaderName: 'X-CSRFToken'
})
let client = new coreapi.Client({auth: auth});
console.log(client);

function markableHandler() {
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
    var preview = $("#preview");
    for (var i = 0; i < images.length; i++) {
        image = images[i];
        var img = $("<img></img>")
            .addClass("gallery-thumbnail")
            .addClass("gallery-markable")
            .attr({src: image.thumbnail_src, id: image.id})

        var thumb_div = $("<div></div>")
            .addClass("gallery-preview")
            .append(img)
        preview.append(thumb_div);
    }
    $(".gallery-markable" ).click(markableHandler);
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
        images = results[i]['image_ids'].sort().join();
        console.log(images);
        galleryId = results[i]['id'];
        galleries[images] = galleryId;
    }
});

var csrf_token = $('input[name=csrfmiddlewaretoken]').attr('value');
console.log(csrf_token);

function replaceWithUploaded(imagePk, img, progress_bar) {
    progress_bar.remove();
    let action = ["api", "images", "read"];
    let params = {id: imagePk};
    console.log('params', params);
    client.action(schema, action, params).then(function(result) {
        console.log('get detail for image ' + imagePk, result);
        $(img).attr({id: imagePk, src: result.thumbnail_src})
            .removeClass('obj')
            .addClass('gallery-markable');
        $(img).click(markableHandler);
    });

}

function fileUpload(img, file, progress_bar) {
    var xhr = new XMLHttpRequest();
    console.log("foobar", img, file);
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

    xhr.open("POST", "/blogs/upload/");
    xhr.setRequestHeader('X-CSRFToken', csrf_token);
    var formData = new FormData();
    formData.append('original', file);
    xhr.enctype = 'mutlipart/form-data';

    xhr.onreadystatechange = function() {
        if(xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            console.log('request finished:');
            var imagePk = xhr.responseText;
            console.log('image id: ', imagePk);
            progress_bar.attr({
                "aria-valuenow": "100",
                "style": "width: 100%",
            });
            replaceWithUploaded(imagePk, img, progress_bar)
        }
    }

    xhr.send(formData);
}


function sendFiles(upload_files, upload_progress) {
    var images = document.querySelectorAll(".obj");

    for (var i = 0; i < images.length; i++) {
        file = upload_files[i];
        progress_bar = upload_progress[i];
        fileUpload(images[i], file, progress_bar);
    }
}

// var inputElement = document.getElementById("input");
//inputElement.addEventListener("change", handleFiles, false);

function handleFiles(files) {
    console.log(files);
    var preview = $("#preview");
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
        var img = $("<img></img>")
            .addClass("gallery-thumbnail obj")

        var progress_bar = $("<div></div>")
            .addClass("progress-bar")
            .attr({role: "progressbar", "aria-valuenow": "0", "aria-valuenow": "0",
                   "aria-valuemin": "0", "aria-valuemax": "100"})

        var progress_div = $("<div></div>")
            .addClass("progress gallery-progress-bar")
            .append(progress_bar)

        var thumb_div = $("<div></div>")
            .addClass("gallery-preview")
            .append(img)
            .append(progress_div)

        upload_files.push(file);
        upload_progress.push(progress_bar);
        preview.prepend(thumb_div);

        var reader = new FileReader();
        reader.onload = (function(aImg) { return function(e) { aImg.attr({src: e.target.result}); }; })(img);
        reader.readAsDataURL(file);
    }
    sendFiles(upload_files, upload_progress);
}

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
    console.log('handle insert');
    var marked = $("img.border");
    var imagePks = [];
    for (var i = 0; i < marked.length; i++) {
        imagePks.push(parseInt($(marked[i]).attr("id")));
    }
    var ckForm = getCkEditorInstance();
    if (imagePks.length == 0) {
        console.log('no media to add');
    } else if (imagePks.length == 1) {
        var imgPk = imagePks[0];
        var templateTag = "{" + "% " + "blog_image " + imgPk + " %" + "}";
        ckForm.insertHtml(templateTag);
    } else {
        addGallery(imagePks, ckForm);
    }
}

$('#insert').click(handleImageInsert);
