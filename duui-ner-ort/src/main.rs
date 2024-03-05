use std::sync::{Arc, Mutex};
use std::{collections::HashMap, env};

use actix_files::NamedFile;
use actix_web::rt::task::spawn_blocking;
use actix_web::{get, post, web, App, HttpResponse, HttpServer, Result};

use clap::{Parser, ValueEnum};
use rust_bert::pipelines::common::ModelResource;
use rust_bert::pipelines::ner::{Entity, NERModel};
use rust_bert::pipelines::token_classification::TokenClassificationConfig;
use rust_bert::resources::RemoteResource;
use rust_bert::roberta::{RobertaConfigResources, RobertaModelResources, RobertaVocabResources};
use serde::{Deserialize, Serialize};

use utoipa::{OpenApi, ToSchema};
use utoipa_swagger_ui::SwaggerUi;

#[derive(Serialize, ToSchema)]
struct TextImagerCapability {
    // List of supported languages by the annotator
    // TODO how to handle language?
    // - ISO 639-1 (two letter codes) as default in meta data
    // - ISO 639-3 (three letters) optionally in extra meta to allow a finer mapping
    supported_languages: Vec<String>,
    // Are results on same inputs reproducible without side effects?
    reproducible: bool,
}

#[derive(Serialize, ToSchema)]
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

#[
    utoipa::path(
        path = "/v1/documentation",
        responses(
            (status = 200, body = TextImagerDocumentation, content_type = "application/json"),
        )
    )
]
#[get("/v1/documentation")]
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

#[
    utoipa::path(
        path = "/v1/communication_layer",
        responses(
            (status = 200, body = String, content_type = "application/x-lua"),
        )
    )
]
#[get("/v1/communication_layer")]
async fn get_v1_communication_layer() -> Result<NamedFile> {
    Ok(NamedFile::open_async("communication_layer.lua").await?)
}

#[derive(Debug, Serialize, Deserialize, ToSchema)]
struct TextImagerRequest {
    text: String,
    language: String,
    sentences: Vec<SentenceOffsets>,
}

#[derive(Debug, Serialize, Deserialize, ToSchema)]
struct SentenceOffsets {
    begin: usize,
    end: usize,
}

#[derive(Debug, Serialize, Deserialize, ToSchema)]
struct TextImagerPrediction {
    pub label: String,
    pub begin: usize,
    pub end: usize,
}

impl TextImagerPrediction {
    pub fn with_offset(mut self, offset: usize) -> Self {
        self.begin += offset;
        self.end += offset;
        self
    }
}

#[derive(Debug, Serialize, Deserialize, Default, ToSchema)]
struct TextImagerResponse {
    predictions: Vec<TextImagerPrediction>,
    meta: Option<HashMap<String, String>>,
}

impl From<Entity> for TextImagerPrediction {
    fn from(entity: Entity) -> Self {
        let mut begin = entity.offset.begin as usize;
        let end = entity.offset.end as usize;

        let word = entity.word.as_str();
        if word.starts_with(char::is_whitespace) {
            let word_len = word.len();
            let stripped_word_len = word.trim_start().len();
            begin += word_len - stripped_word_len;
        }

        Self {
            label: entity.label,
            begin,
            end,
        }
    }
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
async fn post_v1_process(
    request: web::Json<TextImagerRequest>,
    state: web::Data<Arc<AppState>>,
) -> HttpResponse {
    let (offsets, sentences): (Vec<usize>, Vec<&'_ str>) = request
        .sentences
        .iter()
        .map(|sentence| (sentence.begin, &request.text[sentence.begin..=sentence.end]))
        .unzip();

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
    HttpResponse::Ok().json(TextImagerResponse {
        predictions,
        ..Default::default()
    })
}

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

struct AppState {
    model: Mutex<NERModel>,
    batch_size: usize,
}

#[actix_web::main]
async fn main() -> anyhow::Result<()> {
    env_logger::init();

    #[derive(OpenApi)]
    #[openapi(
        paths(get_v1_communication_layer, get_v1_documentation, post_v1_process,),
        components(schemas(
            SentenceOffsets,
            TextImagerCapability,
            TextImagerDocumentation,
            TextImagerPrediction,
            TextImagerRequest,
            TextImagerResponse,
        ))
    )]
    struct ApiDoc;
    let openapi = ApiDoc::openapi();

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
    let state = web::Data::new(Arc::new(AppState {
        model: Mutex::new(model),
        batch_size: args.batch_size,
    }));

    // Configure server to accept all requests as JSON
    // regardless of set Content-Type and enable large request bodies
    let accept_all = |_| true;
    let json_config = web::JsonConfig::default()
        .content_type_required(false)
        .content_type(accept_all)
        .limit(args.limit);

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .wrap(actix_web::middleware::Logger::default())
            .wrap(actix_web::middleware::Logger::new("%a %{User-Agent}i"))
            .wrap(actix_web::middleware::Compress::default())
            .wrap(
                actix_web::middleware::DefaultHeaders::default()
                    .add(("Content-Type", "application/json")),
            )
            .app_data(json_config.clone())
            .service(get_v1_documentation)
            .service(get_v1_communication_layer)
            .service(post_v1_process)
            .service(
                SwaggerUi::new("/swagger-ui/{_:.*}").url("/api-docs/openapi.json", openapi.clone()),
            )
    })
    .bind((args.address, args.port))?
    .workers(args.workers)
    .run()
    .await
    .map_err(anyhow::Error::from)
}
