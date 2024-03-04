use std::sync::{Arc, Mutex};
use std::{collections::HashMap, env, path::PathBuf};

use actix_files::NamedFile;
use actix_web::rt::task::spawn_blocking;
use actix_web::{web, App, HttpResponse, HttpServer, Result};

use clap::{Parser, ValueEnum};
use rust_bert::pipelines::common::ModelResource;
use rust_bert::pipelines::ner::{Entity, NERModel};
use rust_bert::pipelines::token_classification::TokenClassificationConfig;

use rust_bert::resources::RemoteResource;
use rust_bert::roberta::{RobertaModelResources, RobertaVocabResources, RobertaConfigResources};
use serde::{Deserialize, Serialize};

#[allow(clippy::upper_case_acronyms)]
#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum ImplementedProviders {
    CPU,
    CUDA,
}

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long, default_value = "localhost")]
    address: String,

    #[arg(short, long, default_value_t = 9714)]
    port: u16,

    #[arg(short, long, default_value_t = 4)]
    workers: usize,

    #[arg(short, long, default_value = "cuda")]
    device: ImplementedProviders,

    #[arg(long, default_value_t = 0)]
    device_id: usize,

    #[arg(short, long)]
    threads: Option<usize>,

    #[arg(
        short,
        long,
        default_value_t = 128,
        help = "The batch size for processing"
    )]
    batch_size: usize,

    #[arg(long, default_value_t = 16_777_216, help = "The request size limit")]
    limit: usize,
    // #[arg(short, long, default_value = "model/rust_model.ot")]
    // model_path: String,

    // #[arg(short, long, default_value = "model/config.json")]
    // config_path: String,

    // #[arg(short, long, default_value = "model/vocab.json")]
    // vocab_path: String,
}

#[derive(Serialize)]
struct TextImagerCapability {
    // List of supported languages by the annotator
    // TODO how to handle language?
    // - ISO 639-1 (two letter codes) as default in meta data
    // - ISO 639-3 (three letters) optionally in extra meta to allow a finer mapping
    supported_languages: Vec<String>,
    // Are results on same inputs reproducible without side effects?
    reproducible: bool,
}

#[derive(Serialize)]
struct TextImagerDocumentation {
    // Name of this annotator
    annotator_name: String,

    // Version of this annotator
    version: String,

    // Annotator implementation language (Python, Java, ...)
    implementation_lang: Option<String>,

    // Optional map of additional meta data
    meta: Option<HashMap<String, String>>,

    // Docker container id, if any
    docker_container_id: Option<String>,

    // Optional map of supported parameters
    parameters: Option<HashMap<String, String>>,

    // Capabilities of this annotator
    capability: TextImagerCapability,

    // Analysis engine XML, if available
    implementation_specific: Option<String>,
}

async fn get_v1_documentation() -> HttpResponse {
    HttpResponse::Ok().json(TextImagerDocumentation {
        annotator_name: "duui-ner-ort".into(),
        version: env!("CARGO_PKG_VERSION").into(),
        implementation_lang: Some(format!("Rust {}", env!("CARGO_PKG_RUST_VERSION"))),
        meta: None,
        docker_container_id: None,
        parameters: None,
        capability: TextImagerCapability {
            supported_languages: vec!["de".into()],
            reproducible: true,
        },
        implementation_specific: None,
    })
}

async fn get_v1_communication_layer() -> Result<NamedFile> {
    Ok(NamedFile::open_async("communication_layer.lua").await?)
}

#[derive(Debug, Serialize, Deserialize)]
struct DkproSentence {
    begin: usize,
    end: usize,
}

#[derive(Debug, Serialize, Deserialize)]
struct TextImagerRequest {
    text: String,
    language: String,
    sentences: Vec<DkproSentence>,
}

async fn post_v1_process(
    request: web::Json<TextImagerRequest>,
    state: web::Data<Arc<AppState>>,
) -> HttpResponse {
    let entities: Vec<Vec<Entity>> = request
        .sentences
        .iter()
        .map(|sentence| &request.text[sentence.begin..sentence.end])
        .collect::<Vec<&'_ str>>()
        .windows(state.get_ref().batch_size)
        .flat_map(|batch| {
            state
                .get_ref()
                .model
                .lock()
                .unwrap()
                .predict_full_entities(batch)
        })
        .collect();
    HttpResponse::Ok().json(entities)
}

struct AppState {
    model: Mutex<NERModel>,
    batch_size: usize,
}

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    let args: Args = Args::parse();

    let model = spawn_blocking(|| {
        NERModel::new(TokenClassificationConfig {
            model_type: rust_bert::pipelines::common::ModelType::XLMRoberta,
            model_resource: ModelResource::Torch(Box::new(RemoteResource::from_pretrained(
                RobertaModelResources::XLM_ROBERTA_NER_DE,
            ))),
            config_resource: Box::new(RemoteResource::from_pretrained(
                RobertaConfigResources::XLM_ROBERTA_NER_DE,
            )),
            vocab_resource: Box::new(RemoteResource::from_pretrained(
                RobertaVocabResources::XLM_ROBERTA_NER_DE,
            )),
            ..Default::default()
        })
        .unwrap()
    })
    .await?;
    let state = web::Data::new(AppState {
        model: Mutex::new(model),
        batch_size: args.batch_size,
    });

    let accept_all = |_| true;
    let json_config = web::JsonConfig::default()
        .content_type_required(false)
        .content_type(accept_all)
        .limit(args.limit);

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .wrap(actix_web::middleware::Logger::default())
            .wrap(actix_web::middleware::Compress::default())
            .wrap(
                actix_web::middleware::DefaultHeaders::default()
                    .add(("Content-Type", "application/json")),
            )
            .app_data(json_config.clone())
            .service(web::resource("/v1/documentation").route(web::get().to(get_v1_documentation)))
            .service(
                web::resource("/v1/communication_layer")
                    .route(web::get().to(get_v1_communication_layer)),
            )
            .service(web::resource("/v1/process").route(web::post().to(post_v1_process)))
    })
    .bind((args.address, args.port))?
    .workers(args.workers)
    .run()
    .await
    .map_err(anyhow::Error::from)
}
