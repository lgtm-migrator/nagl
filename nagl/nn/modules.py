from typing import Dict, List, Optional, Type, Union

import torch
from typing_extensions import Literal

from nagl.molecules import DGLMolecule, DGLMoleculeBatch
from nagl.nn import ActivationFunction, SequentialLayers
from nagl.nn.gcn import GCNStack, SAGEConvStack
from nagl.nn.pooling import PoolingLayer
from nagl.nn.postprocess import PostprocessLayer

GCNArchitecture = Literal["SAGEConv"]

_GRAPH_ARCHITECTURES: Dict[GCNArchitecture, Type[GCNStack]] = {
    "SAGEConv": SAGEConvStack,
    # "GINConv": GINConvStack,
}


class ConvolutionModule(torch.nn.Module):
    """A module that applies a series of graph convolutions to a given input molecule."""

    def __init__(
        self,
        architecture: GCNArchitecture,
        in_feats: int,
        hidden_feats: List[int],
        activation: Optional[List[ActivationFunction]] = None,
        dropout: Optional[List[float]] = None,
    ):

        super().__init__()

        self.gcn_layers = _GRAPH_ARCHITECTURES[architecture](
            in_feats=in_feats,
            hidden_feats=hidden_feats,
            activation=activation,
            dropout=dropout,
        )

    def forward(self, molecule: Union[DGLMolecule, DGLMoleculeBatch]):

        # The input graph will be heterogeneous - the edges are split into forward
        # edge types and their symmetric reverse counterparts. The convolution layer
        # doesn't need this information and hence we produce a homogeneous graph for
        # it to operate on with only a single edge type.
        molecule.graph.ndata["h"] = self.gcn_layers(
            molecule.homograph, molecule.atom_features
        )


class ReadoutModule(torch.nn.Module):
    """A module that transforms the node features generated by a series of graph
    convolutions via propagation through a pooling, readout and optional postprocess
    layer.
    """

    def __init__(
        self,
        pooling_layer: PoolingLayer,
        readout_layers: SequentialLayers,
        postprocess_layer: Optional[PostprocessLayer] = None,
    ):
        """

        Args:
            pooling_layer: The pooling layer that will concatenate the node features
                computed by a graph convolution into appropriate extended features (e.g.
                bond or angle features). The concatenated features will be provided as
                input to the dense readout layers.
            readout_layers: The dense NN readout layers to apply to the output of the
                pooling layers.
            postprocess_layer: A (optional) postprocessing layer to apply to the output
                of the readout layers
        """

        super().__init__()

        self.pooling_layer = pooling_layer
        self.readout_layers = readout_layers
        self.postprocess_layer = postprocess_layer

    def forward(self, molecule: Union[DGLMolecule, DGLMoleculeBatch]) -> torch.Tensor:

        x = self.pooling_layer.forward(molecule)
        x = self.readout_layers.forward(x)

        if self.postprocess_layer is not None:
            x = self.postprocess_layer.forward(molecule, x)

        return x
