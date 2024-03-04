use std::{collections::HashMap, env, path::PathBuf};

use serde::Serialize;
use serde_json::Value;
use xitca_web::{
    body::{self, ResponseBody},
    error::Error,
    handler::{
        handler_service,
        json::{Json, LazyJson},
        Responder,
    },
    http::{const_header_value::JSON, header::CONTENT_TYPE, Response, WebResponse},
    route::{get, post},
    App,
};

use anyhow::anyhow;
use clap::{Parser, ValueEnum};
use ndarray::{Array2, Axis};
use ndarray_stats::QuantileExt;
// use ort::{CUDAExecutionProvider, ExecutionProvider, Session};
use rayon::iter::{IntoParallelIterator, ParallelIterator};
use rayon::slice::ParallelSlice;
use rust_tokenizers::Mask;
use rust_tokenizers::{tokenizer::Tokenizer, vocab::Vocab};

#[allow(clippy::upper_case_acronyms)]
#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum ImplementedProviders {
    CPU,
    CUDA,
}

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(short, long, default_value = "0.0.0.0")]
    host: String,

    #[arg(short, long, default_value_t = 9714)]
    port: usize,

    #[arg(short, long, default_value = "cpu")]
    device: ImplementedProviders,

    #[arg(long, default_value_t = 0)]
    device_id: usize,

    #[arg(short, long)]
    threads: Option<usize>,

    #[arg(short, long, default_value_t = 128)]
    batch_size: usize,

    #[arg(short, long, default_value = "onnx/model.onnx")]
    model: PathBuf,

    #[arg(short, long, default_value = "onnx/sentencepiece.bpe.model")]
    vocab: PathBuf,

    // #[arg(short, long, value_enum, default_value = "last")]
    // aggregation: Aggregation,
    #[arg()]
    corpus: PathBuf,
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

async fn get_v1_documentation() -> Result<serde_json::Value, Error> {
    serde_json::to_value(TextImagerDocumentation {
        annotator_name: "duui-ner-ort".into(),
        version: env!("CARGO_PKG_VERSION").into(),
        implementation_lang: Some(format!("Rust {}", env!("CARGO_PKG_RUST_VERSION")).into()),
        meta: None,
        docker_container_id: None,
        parameters: None,
        capability: TextImagerCapability {
            supported_languages: vec!["de".into()],
            reproducible: true,
        },
        implementation_specific: None,
    })
    .map_err(|err| Error::from(err))
}

#[derive(serde::Deserialize)]
struct DkproSentence {
    begin: usize,
    end: usize,
}

#[derive(serde::Deserialize)]
struct TextImagerRequest<'a> {
    text: &'a str,
    language: &'a str,
    sentences: Vec<DkproSentence>,
}

async fn post_v1_process(lazy: LazyJson<TextImagerRequest<'_>>) -> Result<&'static str, Error> {
    let TextImagerRequest {
        text,
        language,
        sentences,
    } = lazy.deserialize()?;
    Ok("ok")
}

fn main() -> std::io::Result<()> {
    App::new()
        .at(
            "/v1/documentation",
            get(handler_service(get_v1_documentation)),
        )
        // .at("/v1/process", post(handler_service(post_v1_process)))
        .serve()
        .bind("localhost:8080")?
        .run()
        .wait()
}
