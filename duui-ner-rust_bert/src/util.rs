use rust_bert::bert::{BertConfigResources, BertModelResources, BertVocabResources};
use rust_bert::pipelines::common::ModelResource;
use rust_bert::pipelines::token_classification::TokenClassificationConfig;
use rust_bert::resources::RemoteResource;
use rust_bert::roberta::{RobertaConfigResources, RobertaModelResources, RobertaVocabResources};

use tch::Device;

pub fn parse_device(device: &str) -> anyhow::Result<Device> {
    match device.split(':').collect::<Vec<_>>().as_slice() {
        ["cpu"] => Ok(Device::Cpu),
        ["cuda" | "gpu"] => Ok(Device::Cuda(0)),
        ["cuda" | "gpu", index] => Ok(Device::Cuda(index.parse()?)),
        ["mps"] => Ok(Device::Mps),
        ["vulkan"] => Ok(Device::Vulkan),
        _ => anyhow::bail!("Invalid device choice: {device}"),
    }
}

#[derive(Debug, Clone)]
pub enum ModelChoiceAndLanguages {
    Bert,
    XlmRoberta(String),
}

pub fn parse_model_arg(model: &str) -> anyhow::Result<ModelChoiceAndLanguages> {
    match model
        .to_lowercase()
        .as_str()
        .split(':')
        .collect::<Vec<&str>>()
        .as_slice()
    {
        ["bert"] => Ok(ModelChoiceAndLanguages::Bert),
        ["xlm-roberta"] => Ok(ModelChoiceAndLanguages::XlmRoberta("de".into())),
        ["xlm-roberta", lang] => Ok(ModelChoiceAndLanguages::XlmRoberta((*lang).into())),
        _ => anyhow::bail!("Invalid model choice: {model}"),
    }
}

pub fn get_model_config(
    model: ModelChoiceAndLanguages,
    batch_size: usize,
    device: Device,
) -> anyhow::Result<TokenClassificationConfig> {
    match model {
        ModelChoiceAndLanguages::Bert => Ok(TokenClassificationConfig {
            model_type: rust_bert::pipelines::common::ModelType::Bert,
            model_resource: ModelResource::Torch(box_resource(BertModelResources::BERT_NER)),
            config_resource: box_resource(BertConfigResources::BERT_NER),
            vocab_resource: box_resource(BertVocabResources::BERT_NER),
            batch_size,
            device,
            ..Default::default()
        }),
        ModelChoiceAndLanguages::XlmRoberta(lang) => {
            let choice = match lang.to_lowercase().as_str() {
                "de" => (
                    RobertaModelResources::XLM_ROBERTA_NER_DE,
                    RobertaConfigResources::XLM_ROBERTA_NER_DE,
                    RobertaVocabResources::XLM_ROBERTA_NER_DE,
                ),
                "en" => (
                    RobertaModelResources::XLM_ROBERTA_NER_EN,
                    RobertaConfigResources::XLM_ROBERTA_NER_EN,
                    RobertaVocabResources::XLM_ROBERTA_NER_EN,
                ),
                "nl" => (
                    RobertaModelResources::XLM_ROBERTA_NER_NL,
                    RobertaConfigResources::XLM_ROBERTA_NER_NL,
                    RobertaVocabResources::XLM_ROBERTA_NER_NL,
                ),
                "es" => (
                    RobertaModelResources::XLM_ROBERTA_NER_ES,
                    RobertaConfigResources::XLM_ROBERTA_NER_ES,
                    RobertaVocabResources::XLM_ROBERTA_NER_ES,
                ),
                unknown => anyhow::bail!("Unknown language: {unknown}"),
            };
            Ok(TokenClassificationConfig {
                model_type: rust_bert::pipelines::common::ModelType::XLMRoberta,
                model_resource: ModelResource::Torch(box_resource(choice.0)),
                config_resource: box_resource(choice.1),
                vocab_resource: box_resource(choice.2),
                batch_size,
                device,
                ..Default::default()
            })
        }
    }
}

fn box_resource(resouce: (&str, &str)) -> Box<RemoteResource> {
    Box::new(RemoteResource::from_pretrained(resouce))
}
