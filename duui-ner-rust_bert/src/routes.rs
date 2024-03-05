use std::sync::{Arc, Mutex};

use actix_files::NamedFile;
use actix_web::{get, post, web, HttpResponse, Result};

use rust_bert::pipelines::ner::{Entity, NERModel};

use crate::schema::*;

pub struct AppState {
    pub model: Mutex<NERModel>,
    pub batch_size: usize,
}

#[
    utoipa::path(
        path = "/v1/documentation",
        responses(
            (status = 200, body = TextImagerDocumentation, content_type = "application/json"),
        )
    )
]
#[get("/v1/documentation")]
pub async fn get_v1_documentation() -> HttpResponse {
    HttpResponse::Ok().json(TextImagerDocumentation {
        annotator_name: "duui-ner-ort".into(),
        capability: TextImagerCapability {
            supported_languages: vec!["de".into()],
            reproducible: true,
        },
        ..Default::default()
    })
}

#[
    utoipa::path(
        path = "/v1/communication_layer",
        responses(
            (status = 200, body = String, content_type = "application/x-lua"),
        )
    )
]
#[get("/v1/communication_layer")]
pub async fn get_v1_communication_layer() -> Result<NamedFile> {
    Ok(NamedFile::open_async("communication_layer.lua").await?)
}

#[
    utoipa::path(
        path = "/v1/process",
        request_body = TextImagerRequest,
        responses(
            (status = 200, body = TextImagerResponse, content_type = "application/json"),
        )
    )
]
#[post("/v1/process")]
pub async fn post_v1_process(
    request: web::Json<TextImagerRequest>,
    state: web::Data<Arc<AppState>>,
) -> HttpResponse {
    let (sentences, offsets): (Vec<String>, Vec<usize>) = request.sentences_and_offsets();

    let state_ref = state.get_ref();
    let sentence_batches = sentences.chunks(state_ref.batch_size).collect::<Vec<_>>();
    let predictions = {
        // Obtain the model lock in a separate scope to release it as soon as possible
        let model = state_ref.model.lock().unwrap();

        sentence_batches
            .into_iter()
            .flat_map(|batch| model.predict_full_entities(batch))
            .collect::<Vec<Vec<Entity>>>()
    };
    let predictions: Vec<TextImagerPrediction> = predictions
        .into_iter()
        .zip(offsets)
        .flat_map(|(entities, offset)| {
            entities
                .into_iter()
                .map(|entity| TextImagerPrediction::from(entity).with_offset(offset))
                .collect::<Vec<TextImagerPrediction>>()
        })
        .collect();
    HttpResponse::Ok().json(TextImagerResponse::new(predictions, None))
}
