mod routes;
mod schema;
mod util;

use std::sync::{Arc, Mutex};

use actix_web::rt::task::spawn_blocking;
use actix_web::{web, App, HttpServer};

use clap::Parser;
use rust_bert::pipelines::ner::NERModel;

use tch::Device;

use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

use routes::*;
use schema::*;
use util::*;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long, default_value = "localhost")]
    address: String,

    #[arg(short, long, default_value_t = 9714)]
    port: u16,

    #[arg(short, long, default_value_t = 2)]
    workers: usize,

    #[arg(short, long, default_value = "cuda:0", value_parser = parse_device)]
    device: Device,

    #[arg(
        short,
        long,
        default_value_t = 128,
        help = "The batch size for the rust_bert::NERModel"
    )]
    batch_size: usize,

    #[arg(long, default_value = "XLM-RoBERTa:de", value_parser = parse_model_arg)]
    model: ModelChoiceAndLanguages,

    #[arg(long, default_value_t = false)]
    load_and_exit: bool,
}

fn get_json_config() -> web::JsonConfig {
    // Configure server to accept all requests as JSON
    // regardless of set Content-Type and enable large request bodies
    let accept_all = |_| true;
    let limit: usize = std::env::var("MAX_PAYLOAD_SIZE")
        .unwrap_or_else(|_| "16777215".to_string())
        .parse()
        .unwrap_or(16_777_215);
    web::JsonConfig::default()
        .content_type_required(false)
        .content_type(accept_all)
        .limit(limit)
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

    let config = get_model_config(args.model, args.batch_size, args.device)?;

    if args.load_and_exit {
        NERModel::new(config)?;
        return Ok(());
    }

    let model = spawn_blocking(move || NERModel::new(config).unwrap()).await?;

    let state = web::Data::new(Arc::new(AppState {
        model: Mutex::new(model),
        batch_size: args.batch_size,
    }));
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
            .app_data(get_json_config())
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

#[cfg(test)]
mod test {
    use actix_web::test;

    use rust_bert::pipelines::common::ModelResource;
    use rust_bert::pipelines::token_classification::TokenClassificationConfig;
    use rust_bert::resources::RemoteResource;
    use rust_bert::roberta::{
        RobertaConfigResources, RobertaModelResources, RobertaVocabResources,
    };

    use super::*;

    const TEXT: &str = "Barack Obama ist ein US-amerikanischer Politiker der Demokratischen Partei. Er war von 2009 bis 2017 der 44. Präsident der Vereinigten Staaten.";

    const SENTENCE_OFFSETS: [SentenceOffsets; 2] = [
        SentenceOffsets { begin: 0, end: 74 },
        SentenceOffsets {
            begin: 76,
            end: 143,
        },
    ];

    #[actix_web::test]
    async fn test_app() -> anyhow::Result<()> {
        let model = spawn_blocking(move || {
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
                batch_size: 4,
                ..Default::default()
            })
            .unwrap()
        })
        .await?;
        let state = web::Data::new(Arc::new(AppState {
            model: Mutex::new(model),
            batch_size: 4,
        }));
        let json_config = get_json_config();
        let app = test::init_service(
            App::new()
                .app_data(state.clone())
                .wrap(actix_web::middleware::Logger::default())
                .wrap(
                    actix_web::middleware::DefaultHeaders::default()
                        .add(("Content-Type", "application/json")),
                )
                .app_data(json_config.clone())
                .service(get_v1_documentation)
                .service(get_v1_communication_layer)
                .service(post_v1_process),
        )
        .await;

        let request = test::TestRequest::post()
            .uri("/v1/process")
            .set_json(TextImagerRequest {
                text: TEXT.into(),
                language: "de".into(),
                sentences: SENTENCE_OFFSETS.into_iter().collect(),
            })
            .to_request();

        let result: TextImagerResponse = test::call_and_read_body_json(&app, request).await;

        assert_eq!(
            vec![
                TextImagerPrediction::new("PER", 0, 12,),
                TextImagerPrediction::new("MISC", 21, 38,),
                TextImagerPrediction::new("ORG", 53, 74,),
                TextImagerPrediction::new("LOC", 123, 142,)
            ],
            result.predictions
        );
        Ok(())
    }
}
